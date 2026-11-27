from datetime import datetime, timezone
from ipaddress import IPv4Address
from unittest.mock import Mock

import pytest
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.models import AlertResponse, DeviceCreate, DeviceResponse, StatusUpdate
from app.repositories import mongo_device_repository as mongo_repository
from app.services.device_service import DeviceAlreadyExistsError


@pytest.fixture
def repository_and_collections(monkeypatch):
    monkeypatch.setattr(mongo_repository, "DEVICES_COLLECTION", "test_devices")
    monkeypatch.setattr(mongo_repository, "ALERTS_COLLECTION", "test_alerts")
    devices = Mock()
    alerts = Mock()
    repository = mongo_repository.MongoDeviceRepository(
        {"test_devices": devices, "test_alerts": alerts}
    )
    return repository, devices, alerts


def make_device() -> DeviceCreate:
    return DeviceCreate(
        device_id="router-01",
        name="Core Router",
        device_type="router",
        ip_address="192.0.2.1",
        status="online",
    )


def device_document(**overrides) -> dict:
    document = {
        "_id": "mongo-id",
        "device_id": "router-01",
        "name": "Core Router",
        "device_type": "router",
        "ip_address": "192.0.2.1",
        "status": "online",
    }
    document.update(overrides)
    return document


def test_device_repository_methods_convert_documents_and_fields(
    repository_and_collections,
) -> None:
    repository, devices, alerts = repository_and_collections
    device = make_device()
    devices.find.return_value = [device_document()]
    devices.find_one.return_value = device_document()
    devices.find_one_and_update.return_value = device_document(status="offline")
    alert_time = datetime(2026, 11, 27, tzinfo=timezone.utc)
    alert = AlertResponse(
        device_id="router-01",
        message="Device router-01 went offline.",
        timestamp=alert_time,
    )
    alerts.find.return_value = [{"_id": "alert-id", **alert.model_dump()}]

    added = repository.add_device(device)
    listed_devices = repository.list_devices()
    found = repository.get_device("router-01")
    updated = repository.update_status(
        "router-01", StatusUpdate(status="offline")
    )
    saved_alert = repository.save_alert(alert)
    listed_alerts = repository.list_alerts()

    assert added == DeviceResponse.model_validate(device_document())
    devices.insert_one.assert_called_once_with(
        {
            "device_id": "router-01",
            "name": "Core Router",
            "device_type": "router",
            "ip_address": "192.0.2.1",
            "status": "online",
            "location": None,
        }
    )
    assert listed_devices[0].ip_address == IPv4Address("192.0.2.1")
    assert found == added
    assert updated is not None and updated.status == "offline"
    devices.find_one_and_update.assert_called_once_with(
        {"device_id": "router-01"},
        {"$set": {"status": "offline"}},
        return_document=ReturnDocument.AFTER,
    )
    assert saved_alert.timestamp == alert_time
    assert isinstance(saved_alert.timestamp, datetime)
    assert listed_alerts[0].timestamp == alert_time
    assert "_id" not in devices.insert_one.call_args.args[0]


def test_mongo_repository_stores_and_preserves_location(
    repository_and_collections,
) -> None:
    repository, devices, _ = repository_and_collections
    device = DeviceCreate(
        device_id="router-01",
        name="Core Router",
        device_type="router",
        ip_address="192.0.2.1",
        location="North Wing",
    )
    stored_document = device_document(location="North Wing")
    devices.find.return_value = [stored_document]
    devices.find_one.return_value = stored_document
    devices.find_one_and_update.return_value = device_document(
        status="offline", location="North Wing"
    )

    created = repository.add_device(device)
    listed = repository.list_devices()
    retrieved = repository.get_device("router-01")
    updated = repository.update_status(
        "router-01", StatusUpdate(status="offline")
    )

    assert devices.insert_one.call_args.args[0]["location"] == "North Wing"
    assert created.location == "North Wing"
    assert listed[0].location == "North Wing"
    assert retrieved is not None and retrieved.location == "North Wing"
    assert updated is not None and updated.location == "North Wing"


def test_add_device_maps_duplicate_key_to_service_exception(
    repository_and_collections,
) -> None:
    repository, devices, _ = repository_and_collections
    devices.insert_one.side_effect = DuplicateKeyError("duplicate key")

    with pytest.raises(DeviceAlreadyExistsError, match="router-01"):
        repository.add_device(make_device())


def test_repository_returns_none_for_missing_device(repository_and_collections) -> None:
    repository, devices, _ = repository_and_collections
    devices.find_one.return_value = None
    devices.find_one_and_update.return_value = None

    assert repository.get_device("missing") is None
    assert repository.update_status("missing", StatusUpdate(status="offline")) is None