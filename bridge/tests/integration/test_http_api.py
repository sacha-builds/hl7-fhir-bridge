"""HTTP endpoint tests using FastAPI's TestClient against a fully-booted app."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bridge.fhir_client import FHIRClient
from bridge.main import create_app
from bridge.metrics import Metrics
from bridge.router import MessageRouter
from bridge.store import MessageStore


@pytest.fixture
def app_with_mock_fhir():
    """Build an app with a no-op lifespan, wiring a mock FHIR directly."""
    fhir_calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        fhir_calls.append(request)
        if request.method == "GET":
            path = request.url.path
            if path.endswith("/Patient"):
                return httpx.Response(
                    200,
                    headers={"content-type": "application/fhir+json"},
                    json={
                        "resourceType": "Bundle",
                        "type": "searchset",
                        "entry": [
                            {
                                "resource": {
                                    "resourceType": "Patient",
                                    "id": "abc",
                                }
                            }
                        ],
                    },
                )
        return httpx.Response(
            201,
            headers={
                "Location": "Patient/1/_history/1",
                "content-type": "application/fhir+json",
            },
            json={"resourceType": "Patient", "id": "1"},
        )

    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)

    fhir_client = FHIRClient("http://fhir.test/fhir", client=http)
    store = MessageStore()
    metrics = Metrics()
    router = MessageRouter(fhir_client, store=store, metrics=metrics)

    @asynccontextmanager
    async def test_lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.fhir_client = fhir_client
        app.state.store = store
        app.state.metrics = metrics
        app.state.router = router
        app.state.mllp = None
        yield

    app = create_app(lifespan_fn=test_lifespan)
    try:
        yield app, fhir_calls
    finally:
        pass


def test_health_returns_ok(app_with_mock_fhir) -> None:
    app, _ = app_with_mock_fhir
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_list_messages_starts_empty(app_with_mock_fhir) -> None:
    app, _ = app_with_mock_fhir
    with TestClient(app) as client:
        response = client.get("/v2/messages")
        assert response.status_code == 200
        assert response.json() == []


def test_get_unknown_message_returns_404(app_with_mock_fhir) -> None:
    app, _ = app_with_mock_fhir
    with TestClient(app) as client:
        response = client.get("/v2/messages/nope")
        assert response.status_code == 404


def test_replay_records_message_and_lists_summary(app_with_mock_fhir) -> None:
    app, _ = app_with_mock_fhir
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    raw = (fixtures / "adt_a01_simple.hl7").read_text()
    with TestClient(app) as client:
        replay = client.post("/v2/replay", json={"message": raw})
        assert replay.status_code == 200
        assert "MSA|AA" in replay.json()["ack"]

        listed = client.get("/v2/messages")
        assert listed.status_code == 200
        summaries = listed.json()
        assert len(summaries) == 1
        assert summaries[0]["message_type"] == "ADT^A01"
        assert summaries[0]["ack_code"] == "AA"
        assert summaries[0]["resource_count"] == 2

        detail = client.get(f"/v2/messages/{summaries[0]['id']}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["raw_v2"] == raw
        kinds = [r["resource_type"] for r in body["resources"]]
        assert kinds == ["Patient", "Encounter"]


def test_websocket_receives_hello_and_live_event(app_with_mock_fhir) -> None:
    app, _ = app_with_mock_fhir
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    raw = (fixtures / "adt_a01_simple.hl7").read_text()
    with TestClient(app) as client, client.websocket_connect("/ws/messages") as ws:
        hello = json.loads(ws.receive_text())
        assert hello["event"] == "hello"

        client.post("/v2/replay", json={"message": raw})

        event = json.loads(ws.receive_text())
        assert event["event"] == "message.received"
        assert event["data"]["message_type"] == "ADT^A01"


def test_fhir_proxy_forwards_reads_to_upstream(app_with_mock_fhir) -> None:
    app, fhir_calls = app_with_mock_fhir
    with TestClient(app) as client:
        response = client.get("/fhir/Patient", params={"_count": "10"})
        assert response.status_code == 200
        body = response.json()
        assert body["resourceType"] == "Bundle"

    assert any(
        request.method == "GET" and request.url.path.endswith("/Patient") for request in fhir_calls
    )


def test_metrics_endpoint_reflects_processed_messages(app_with_mock_fhir) -> None:
    app, _ = app_with_mock_fhir
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    raw = (fixtures / "adt_a01_simple.hl7").read_text()
    with TestClient(app) as client:
        before = client.get("/metrics").json()
        assert before["messages_total"] == 0

        client.post("/v2/replay", json={"message": raw})

        after = client.get("/metrics").json()
        assert after["messages_total"] == 1
        assert after["messages_by_type"] == {"ADT^A01": 1}
        assert after["messages_by_ack_code"] == {"AA": 1}
        assert after["resources_written"]["Patient"] == 1
        assert after["resources_written"]["Encounter"] == 1


def test_delete_v2_messages_clears_inbox_and_metrics(app_with_mock_fhir) -> None:
    app, _ = app_with_mock_fhir
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    raw = (fixtures / "adt_a01_simple.hl7").read_text()
    with TestClient(app) as client:
        client.post("/v2/replay", json={"message": raw})
        assert len(client.get("/v2/messages").json()) == 1
        assert client.get("/metrics").json()["messages_total"] == 1

        delete = client.delete("/v2/messages")
        assert delete.status_code == 204

        assert client.get("/v2/messages").json() == []
        assert client.get("/metrics").json()["messages_total"] == 0
