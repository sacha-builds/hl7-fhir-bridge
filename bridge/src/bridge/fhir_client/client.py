from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import structlog

log = structlog.get_logger()


class FHIRClient:
    """Thin async client for a FHIR R4 REST server (HAPI, Medplum, HealthLake).

    Supports optional OAuth2 client-credentials when `oauth_token_url`,
    `oauth_client_id`, and `oauth_client_secret` are provided. Medplum's
    free tier uses this flow: the client POSTs those credentials to the
    token endpoint, caches the returned access token, and attaches it as
    a Bearer header on every FHIR request. Tokens are refreshed ~60s
    before expiry.
    """

    def __init__(
        self,
        base_url: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
        oauth_token_url: str | None = None,
        oauth_client_id: str | None = None,
        oauth_client_secret: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None
        self._oauth_token_url = oauth_token_url
        self._oauth_client_id = oauth_client_id
        self._oauth_client_secret = oauth_client_secret
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._token_lock = asyncio.Lock()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def conditional_create(
        self,
        resource: Any,
        *,
        identifier_query: str | None = None,
    ) -> dict[str, Any]:
        """Create the resource unless one already exists matching the query.

        When `identifier_query` is provided (e.g. ``"urn:id:HOSP|MRN12345"``),
        we issue an `If-None-Exist` conditional create per the FHIR spec
        (§ RESTful API — Create). This is the idempotent pattern the v2-to-
        FHIR IG recommends so replaying a v2 feed does not duplicate records.
        """
        resource_type = resource.__class__.__name__
        url = f"{self.base_url}/{resource_type}"
        headers = await self._headers()
        if identifier_query:
            headers["If-None-Exist"] = f"identifier={identifier_query}"
        body = resource.model_dump(by_alias=True, exclude_none=True, mode="json")
        response = await self._client.post(url, json=body, headers=headers)
        response.raise_for_status()
        log.info(
            "fhir.create",
            resource_type=resource_type,
            status=response.status_code,
            location=response.headers.get("Location"),
        )
        return self._parse_body(response)

    async def conditional_update(
        self,
        resource: Any,
        *,
        identifier_query: str,
    ) -> dict[str, Any]:
        """Update-or-create by identifier via FHIR conditional update.

        Per the FHIR spec (§ RESTful API — Update), a PUT to a search URL
        (`PUT /{Type}?identifier=...`) updates the matching resource or
        creates it if none exists. This is how we apply ADT^A03/A08 changes
        without needing the server-assigned id.
        """
        resource_type = resource.__class__.__name__
        url = f"{self.base_url}/{resource_type}"
        params = {"identifier": identifier_query}
        headers = await self._headers()
        body = resource.model_dump(by_alias=True, exclude_none=True, mode="json")
        response = await self._client.put(url, params=params, json=body, headers=headers)
        response.raise_for_status()
        log.info(
            "fhir.update",
            resource_type=resource_type,
            status=response.status_code,
            location=response.headers.get("Location"),
        )
        return self._parse_body(response)

    async def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json",
        }
        token = await self._access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _access_token(self) -> str | None:
        if not (self._oauth_token_url and self._oauth_client_id and self._oauth_client_secret):
            return None
        # Refresh ~60s before expiry to avoid edge cases
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        async with self._token_lock:
            # Re-check after acquiring the lock in case another coroutine refreshed
            if self._token and time.time() < self._token_expires_at - 60:
                return self._token
            response = await self._client.post(
                self._oauth_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._oauth_client_id,
                    "client_secret": self._oauth_client_secret,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            body = response.json()
            self._token = body["access_token"]
            self._token_expires_at = time.time() + float(body.get("expires_in", 3600))
            log.info(
                "fhir.oauth.token_refreshed",
                expires_in=body.get("expires_in"),
            )
            return self._token

    @staticmethod
    def _parse_body(response: httpx.Response) -> dict[str, Any]:
        if not response.content:
            return {"status": response.status_code}
        return response.json()  # type: ignore[no-any-return]
