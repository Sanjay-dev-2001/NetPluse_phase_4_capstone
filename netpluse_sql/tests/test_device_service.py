import pytest

from app.models import DeviceCreate, StatusUpdate
from app.repositories.device_repository import InMemoryDeviceRepository
from app.services.device_service import (
    DeviceAlreadyExistsError,
    DeviceNotFoundError,
    DeviceService,
)


@pytest.fixture
def service_and_repository() -> tuple[DeviceService, InMemoryDeviceRepository]:
    repository = InMemoryDeviceRepository()
    return DeviceService(repository), repository


def make_device(device_id: str, status: str = "online") -> DeviceCreate:
    return DeviceCreate(
        device_id=device_id,
        name="router-1",
        device_type="router",
        ip_address="192.0.2.1",
        status=status,
    )


def test_registration(service_and_repository) -> None:
    service, repository = service_and_repository
    registered = service.register(make_device("router-1"))

    assert registered.device_id == "router-1"
    assert registered.status == "online"
    assert service.get("router-1") == registered
    assert service.list() == [registered]
    assert repository.list_alerts() == []


def test_duplicate_registration_raises(service_and_repository) -> None:
    service, _ = service_and_repository
    service.register(make_device("router-1"))

    with pytest.raises(DeviceAlreadyExistsError):
        service.register(make_device("router-1"))


def test_missing_device_raises_not_found(service_and_repository) -> None:
    service, _ = service_and_repository

    with pytest.raises(DeviceNotFoundError):
        service.get("missing")

    with pytest.raises(DeviceNotFoundError):
        service.update_status("missing", StatusUpdate(status="offline"))


def test_initial_offline_registration_does_not_create_alert(
    service_and_repository,
) -> None:
    service, repository = service_and_repository
    registered = service.register(make_device("router-1", status="offline"))

    assert registered.status == "offline"
    assert repository.list_alerts() == []


def test_online_to_offline_creates_one_alert(service_and_repository) -> None:
    service, repository = service_and_repository
    service.register(make_device("router-1"))

    updated = service.update_status("router-1", StatusUpdate(status="offline"))
    alerts = repository.list_alerts()

    assert updated.status == "offline"
    assert len(alerts) == 1
    assert alerts[0].device_id == "router-1"


def test_repeated_offline_update_does_not_create_another_alert(
    service_and_repository,
) -> None:
    service, repository = service_and_repository
    service.register(make_device("router-1"))
    offline = StatusUpdate(status="offline")

    service.update_status("router-1", offline)
    service.update_status("router-1", offline)

    alerts = repository.list_alerts()
    assert len(alerts) == 1
    assert alerts[0].device_id == "router-1"