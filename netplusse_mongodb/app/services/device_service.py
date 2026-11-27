from __future__ import annotations

from app.events import create_offline_alert
from app.models import AlertResponse, DeviceCreate, DeviceResponse, StatusUpdate
from app.repositories.device_repository import DeviceRepository


class DeviceAlreadyExistsError(Exception):
    def __init__(self, device_id: str) -> None:
        super().__init__(f"Device '{device_id}' already exists")


class DeviceNotFoundError(Exception):
    def __init__(self, device_id: str) -> None:
        super().__init__(f"Device '{device_id}' was not found")


class DeviceService:
    def __init__(self, repository: DeviceRepository) -> None:
        self._repository = repository

    def register(self, device: DeviceCreate) -> DeviceResponse:
        if self._repository.get_device(device.device_id) is not None:
            raise DeviceAlreadyExistsError(device.device_id)
        return self._repository.add_device(device)

    def list(self) -> list[DeviceResponse]:
        return self._repository.list_devices()

    def list_alerts(self) -> list[AlertResponse]:
        return self._repository.list_alerts()

    def get(self, device_id: str) -> DeviceResponse:
        device = self._repository.get_device(device_id)
        if device is None:
            raise DeviceNotFoundError(device_id)
        return device

    def update_status(
        self, device_id: str, status_update: StatusUpdate
    ) -> DeviceResponse:
        current = self._repository.get_device(device_id)
        if current is None:
            raise DeviceNotFoundError(device_id)

        updated = self._repository.update_status(device_id, status_update)
        if updated is None:
            raise DeviceNotFoundError(device_id)
        if current.status == "online" and status_update.status == "offline":
            create_offline_alert(self._repository, device_id)
        return updated