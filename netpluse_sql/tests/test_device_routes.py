import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.repositories.device_repository import InMemoryDeviceRepository
from app.repositories.mysql_device_repository import MySqlDeviceRepository
from app.routes.devices import get_device_service
from app.services.device_service import DeviceService


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)

    def get_test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def device_payload():
    return {
        "device_id": "router-01",
        "name": "Core Router",
        "device_type": "router",
        "ip_address": "192.0.2.1",
        "status": "online",
    }


def test_database_routes_preserve_api_and_alert_rules(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.post("/devices", json=device_payload()).status_code == 201
    assert client.post("/devices", json=device_payload()).status_code == 409
    assert client.get("/devices/missing").status_code == 404
    assert client.get("/devices").json() == [device_payload()]
    assert client.patch("/devices/router-01/status", json={"status": "offline"}).status_code == 200
    assert client.patch("/devices/router-01/status", json={"status": "offline"}).status_code == 200
    assert client.get("/devices/router-01").json()["status"] == "offline"
    alerts = client.get("/alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["message"] == "Device router-01 went offline."


def test_alert_failure_rolls_back_status_update(client, monkeypatch):
    assert client.post("/devices", json=device_payload()).status_code == 201

    def fail_save_alert(self, alert):
        raise RuntimeError("alert write failed")

    monkeypatch.setattr(MySqlDeviceRepository, "save_alert", fail_save_alert)
    assert client.patch("/devices/router-01/status", json={"status": "offline"}).status_code == 500
    assert client.get("/devices/router-01").json()["status"] == "online"
    assert client.get("/alerts").json() == []


def test_service_dependency_can_use_in_memory_repository(client):
    service = DeviceService(InMemoryDeviceRepository())
    app.dependency_overrides[get_device_service] = lambda: service
    try:
        assert client.post("/devices", json=device_payload()).status_code == 201
        assert client.get("/devices").json() == [device_payload()]
    finally:
        app.dependency_overrides.pop(get_device_service, None)