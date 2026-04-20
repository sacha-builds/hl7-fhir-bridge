import httpx
import pytest
from fhir.resources.R4B.patient import Patient

from bridge.fhir_client import FHIRClient


@pytest.mark.asyncio
async def test_conditional_create_sends_if_none_exist_header() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["content"] = request.content.decode()
        return httpx.Response(
            201,
            headers={"Location": "Patient/123/_history/1"},
            json={"resourceType": "Patient", "id": "123"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = FHIRClient("http://fhir.test/fhir", client=http)
        patient = Patient(identifier=[{"system": "urn:id:HOSP", "value": "MRN1"}])
        body = await client.conditional_create(patient, identifier_query="urn:id:HOSP|MRN1")

    assert captured["method"] == "POST"
    assert captured["url"] == "http://fhir.test/fhir/Patient"
    assert captured["headers"]["if-none-exist"] == "identifier=urn:id:HOSP|MRN1"
    assert captured["headers"]["content-type"] == "application/fhir+json"
    assert "MRN1" in captured["content"]
    assert body == {"resourceType": "Patient", "id": "123"}


@pytest.mark.asyncio
async def test_conditional_create_without_identifier_query_omits_header() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(201, json={"resourceType": "Patient", "id": "abc"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = FHIRClient("http://fhir.test/fhir", client=http)
        patient = Patient()
        await client.conditional_create(patient)

    assert "if-none-exist" not in captured["headers"]
