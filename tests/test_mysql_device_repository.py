from datetime import datetime, timezone
import os
from uuid import uuid4

import pytest
from pymysql.err import IntegrityError as MySqlIntegrityError
from sqlalchemy import create_engine, delete, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Alert, Device
from app.db.session import Base
from app.models import AlertResponse, DeviceCreate, StatusUpdate
from app.repositories.mysql_device_repository import MySqlDeviceRepository
from app.services.device_service import DeviceAlreadyExistsError, DeviceService


@pytest.fixture
def repository():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield MySqlDeviceRepository(session)
    engine.dispose()


def make_device():
    return DeviceCreate(
        device_id="router-01",
        name="Core Router",
        device_type="router",
        ip_address="192.0.2.1",
    )


def test_repository_crud_and_detached_copies(repository):
    created = repository.add_device(make_device())
    created.name = "changed locally"
    assert repository.get_device("router-01").name == "Core Router"
    assert len(repository.list_devices()) == 1
    assert repository.get_device("missing") is None
    assert repository.update_status("missing", StatusUpdate(status="offline")) is None
    assert repository.update_status("router-01", StatusUpdate(status="offline")).status == "offline"

    alert = AlertResponse(
        device_id="router-01", message="offline", timestamp=datetime.now(timezone.utc)
    )
    saved = repository.save_alert(alert)
    assert saved == alert and saved is not alert
    assert repository.list_alerts() == [alert]


def test_duplicate_is_translated_and_session_recovers(repository):
    repository.add_device(make_device())
    with pytest.raises(DeviceAlreadyExistsError):
        repository.add_device(make_device())
    assert repository.get_device("router-01") is not None


def test_other_integrity_errors_are_not_reported_as_duplicates(repository):
    alert = AlertResponse(device_id="missing", message="offline", timestamp=datetime.now(timezone.utc))
    with pytest.raises(IntegrityError):
        repository.save_alert(alert)
    assert repository.add_device(make_device()).device_id == "router-01"


def test_mysql_duplicate_error_is_translated_and_rolled_back(repository, monkeypatch):
    original_flush = repository._session.flush

    def fail_flush():
        raise IntegrityError("INSERT", {}, MySqlIntegrityError(1062, "Duplicate entry"))

    monkeypatch.setattr(repository._session, "flush", fail_flush)
    with pytest.raises(DeviceAlreadyExistsError):
        repository.add_device(make_device())
    monkeypatch.setattr(repository._session, "flush", original_flush)
    assert repository.add_device(make_device()).device_id == "router-01"


def test_service_business_rules_with_database_repository(repository):
    service = DeviceService(repository)
    service.register(make_device())
    service.update_status("router-01", StatusUpdate(status="offline"))
    service.update_status("router-01", StatusUpdate(status="offline"))
    assert len(service.list_alerts()) == 1


@pytest.mark.skipif(not os.getenv("TEST_MYSQL_URL"), reason="TEST_MYSQL_URL is not set")
def test_repository_against_mysql():
    engine = create_engine(os.environ["TEST_MYSQL_URL"])
    device_id = f"test-{uuid4().hex}"
    try:
        with Session(engine) as session:
            repository = MySqlDeviceRepository(session)
            device = make_device().model_copy(update={"device_id": device_id})
            assert repository.add_device(device).device_id == device_id
            with pytest.raises(DeviceAlreadyExistsError):
                repository.add_device(device)
            assert repository.get_device(device_id) is not None
            assert repository.update_status(device_id, StatusUpdate(status="offline")).status == "offline"
            alert = AlertResponse(device_id=device_id, message="offline", timestamp=datetime.now(timezone.utc))
            repository.save_alert(alert)
            assert any(item.device_id == device_id for item in repository.list_alerts())
    finally:
        with Session(engine) as session:
            session.execute(delete(Alert).where(Alert.device_id == device_id))
            session.execute(delete(Device).where(Device.device_id == device_id))
            session.commit()
        engine.dispose()