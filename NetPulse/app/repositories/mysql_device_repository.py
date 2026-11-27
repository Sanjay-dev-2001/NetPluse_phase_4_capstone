from datetime import timezone
import sqlite3

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Alert, Device
from app.models import AlertResponse, DeviceCreate, DeviceResponse, StatusUpdate
from app.services.device_service import DeviceAlreadyExistsError


def _device_response(device: Device) -> DeviceResponse:
    return DeviceResponse(
        device_id=device.device_id,
        name=device.name,
        device_type=device.device_type,
        ip_address=device.ip_address,
        status=device.status,
    )


def _alert_response(alert: Alert) -> AlertResponse:
    timestamp = alert.timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return AlertResponse(device_id=alert.device_id, message=alert.message, timestamp=timestamp)


def _is_duplicate_key(error: IntegrityError) -> bool:
    original = error.orig
    return (
        bool(original.args) and original.args[0] == 1062
    ) or getattr(original, "sqlite_errorcode", None) in (
        sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY,
        sqlite3.SQLITE_CONSTRAINT_UNIQUE,
    )


class MySqlDeviceRepository:
    def __init__(self, session: Session, *, commit_on_write: bool = True) -> None:
        self._session = session
        self._commit_on_write = commit_on_write

    def _finish_write(self) -> None:
        self._session.flush()
        if self._commit_on_write:
            self._session.commit()

    def add_device(self, device: DeviceCreate) -> DeviceResponse:
        try:
            stored = Device(
                device_id=device.device_id,
                name=device.name,
                device_type=device.device_type,
                ip_address=str(device.ip_address),
                status=device.status,
            )
            self._session.add(stored)
            result = _device_response(stored)
            self._finish_write()
            return result
        except IntegrityError as error:
            self._session.rollback()
            if _is_duplicate_key(error):
                raise DeviceAlreadyExistsError(device.device_id) from error
            raise
        except Exception:
            self._session.rollback()
            raise

    def list_devices(self) -> list[DeviceResponse]:
        return [_device_response(device) for device in self._session.scalars(select(Device))]

    def get_device(self, device_id: str) -> DeviceResponse | None:
        device = self._session.get(Device, device_id)
        return _device_response(device) if device is not None else None

    def update_status(
        self, device_id: str, status_update: StatusUpdate
    ) -> DeviceResponse | None:
        try:
            device = self._session.get(Device, device_id)
            if device is None:
                return None
            device.status = status_update.status
            result = _device_response(device)
            self._finish_write()
            return result
        except Exception:
            self._session.rollback()
            raise

    def save_alert(self, alert: AlertResponse) -> AlertResponse:
        try:
            timestamp = alert.timestamp
            if timestamp.tzinfo is not None:
                timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
            self._session.add(
                Alert(device_id=alert.device_id, message=alert.message, timestamp=timestamp)
            )
            self._finish_write()
            return alert.model_copy(deep=True)
        except Exception:
            self._session.rollback()
            raise

    def list_alerts(self) -> list[AlertResponse]:
        return [
            _alert_response(alert)
            for alert in self._session.scalars(select(Alert).order_by(Alert.id))
        ]