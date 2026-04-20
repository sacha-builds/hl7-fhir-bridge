from fastapi.testclient import TestClient

from bridge import __version__
from bridge.main import app


def test_version_is_set() -> None:
    assert __version__


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__


def test_root_endpoint_reports_service_info() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "HL7 v2 → FHIR Bridge"
    assert body["version"] == __version__
