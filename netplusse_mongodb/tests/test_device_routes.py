from unittest.mock import Mock

from fastapi.testclient import TestClient
import pytest

import app.main as main
from app.main import app
from app.repositories.device_repository import InMemoryDeviceRepository
from app.routes import devices as device_routes
from app.routes.devices import get_device_service
from app.services.device_service import DeviceService


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "get_db", lambda: object())
    monkeypatch.setattr(main, "ensure_indexes", lambda _db: None)
    service = DeviceService(InMemoryDeviceRepository())
    app.dependency_overrides[get_device_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_device_service, None)


def test_startup_initializes_indexes(monkeypatch) -> None:
    database = object()
    ensure_indexes = Mock()
    monkeypatch.setattr(main, "get_db", lambda: database)
    monkeypatch.setattr(main, "ensure_indexes", ensure_indexes)

    with TestClient(app):
        pass

    ensure_indexes.assert_called_once_with(database)


def test_default_service_dependency_uses_mongo_repository(monkeypatch) -> None:
    repository = Mock()
    monkeypatch.setattr(
        device_routes, "MongoDeviceRepository", lambda: repository
    )

    service = get_device_service()
    service.list()

    repository.list_devices.assert_called_once_with()


def device_payload() -> dict[str, str]:
    return {
        "device_id": "router-01",
        "name": "Core Router",
        "device_type": "router",
        "ip_address": "192.0.2.1",
        "status": "online",
    }


def test_device_endpoints_and_transition_alert(client) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    created = client.post("/devices", json=device_payload())
    expected_device = {**device_payload(), "location": None}
    assert created.status_code == 201
    assert created.json() == expected_device
    assert client.post("/devices", json=device_payload()).status_code == 409
    assert client.get("/devices").json() == [expected_device]
    assert client.get("/devices/router-01").json() == expected_device
    assert client.get("/devices/missing").status_code == 404
    assert client.patch(
        "/devices/router-01/status", json={"status": "offline"}
    ).status_code == 200
    assert client.patch(
        "/devices/router-01/status", json={"status": "offline"}
    ).status_code == 200
    assert len(client.get("/alerts").json()) == 1


def test_device_api_accepts_and_returns_location(client) -> None:
    payload = {**device_payload(), "location": "North Wing"}

    created = client.post("/devices", json=payload)

    assert created.status_code == 201
    assert created.json() == payload
    assert client.get("/devices/router-01").json() == payload


def test_invalid_ipv4_address_is_rejected(client) -> None:
    payload = device_payload()
    payload["ip_address"] = "999.1.1.1"

    assert client.post("/devices", json=payload).status_code == 422


def test_openapi_documents_examples_and_error_responses(client) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert "409" in paths["/devices"]["post"]["responses"]
    assert "404" in paths["/devices/{device_id}"]["get"]["responses"]
    assert "404" in paths["/devices/{device_id}/status"]["patch"]["responses"]
    device_schema = schema["components"]["schemas"]["DeviceCreate"]
    assert device_schema["examples"][0]["device_id"] == "router-01"