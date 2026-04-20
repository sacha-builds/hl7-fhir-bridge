from __future__ import annotations

from typing import Any

import httpx
import structlog

log = structlog.get_logger()


class FHIRClient:
    """Thin async client for a FHIR R4 REST server (HAPI, Medplum, HealthLake)."""

    def __init__(
        self,
        base_url: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None

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
        headers = self._headers()
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
        headers = self._headers()
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

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json",
        }

    @staticmethod
    def _parse_body(response: httpx.Response) -> dict[str, Any]:
        if not response.content:
            return {"status": response.status_code}
        return response.json()  # type: ignore[no-any-return]
