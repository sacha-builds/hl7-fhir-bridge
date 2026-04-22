"""OAuth client-credentials flow in FHIRClient (Medplum-style auth)."""

from __future__ import annotations

import httpx
import pytest
from fhir.resources.R4B.patient import Patient

from bridge.fhir_client import FHIRClient


@pytest.mark.asyncio
async def test_no_oauth_config_means_no_auth_header() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(201, json={"resourceType": "Patient", "id": "1"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = FHIRClient("http://fhir.test/fhir", client=http)
        await client.conditional_create(Patient())

    assert "authorization" not in captured["headers"]


@pytest.mark.asyncio
async def test_oauth_fetches_token_and_attaches_bearer() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(
                200,
                json={"access_token": "tok-abc", "expires_in": 3600, "token_type": "Bearer"},
            )
        return httpx.Response(201, json={"resourceType": "Patient", "id": "1"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = FHIRClient(
            "http://fhir.test/fhir",
            client=http,
            oauth_token_url="http://auth.test/oauth/token",
            oauth_client_id="cid",
            oauth_client_secret="secret",
        )
        await client.conditional_create(Patient())

    # First call was the token fetch
    assert calls[0].url.path.endswith("/oauth/token")
    body = dict(pair.split("=", 1) for pair in calls[0].content.decode().split("&"))
    assert body["grant_type"] == "client_credentials"
    assert body["client_id"] == "cid"
    assert body["client_secret"] == "secret"

    # Subsequent FHIR call carried the bearer
    assert calls[1].headers["authorization"] == "Bearer tok-abc"


@pytest.mark.asyncio
async def test_oauth_token_is_cached_across_requests() -> None:
    token_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls
        if request.url.path.endswith("/oauth/token"):
            token_calls += 1
            return httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        return httpx.Response(201, json={"resourceType": "Patient", "id": "1"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = FHIRClient(
            "http://fhir.test/fhir",
            client=http,
            oauth_token_url="http://auth.test/oauth/token",
            oauth_client_id="cid",
            oauth_client_secret="secret",
        )
        await client.conditional_create(Patient())
        await client.conditional_create(Patient())
        await client.conditional_create(Patient())

    assert token_calls == 1
