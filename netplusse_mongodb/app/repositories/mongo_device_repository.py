from typing import Any

from pymongo import ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.config import ALERTS_COLLECTION, DEVICES_COLLECTION
from app.db.mongo import get_db
from app.models import AlertResponse, DeviceCreate, DeviceResponse, StatusUpdate
from app.services.device_service import DeviceAlreadyExistsError


class MongoDeviceRepository:
    def __init__(self, db: Database | None = None) -> None:
        self._db = db if db is not None else get_db()
        self._devices = self._db[DEVICES_COLLECTION]
        self._alerts = self._db[ALERTS_COLLECTION]

    @staticmethod
    def _without_id(document: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in document.items() if key != "_id"}

    def add_device(self, device: DeviceCreate) -> DeviceResponse:
        document = device.model_dump()
        document["ip_address"] = str(device.ip_address)
        try:
            self._devices.insert_one(document)
        except DuplicateKeyError as error:
            raise DeviceAlreadyExistsError(device.device_id) from error
        return DeviceResponse.model_validate(self._without_id(document))

    def list_devices(self) -> list[DeviceResponse]:
        return [
            DeviceResponse.model_validate(self._without_id(document))
            for document in self._devices.find({})
        ]

    def get_device(self, device_id: str) -> DeviceResponse | None:
        document = self._devices.find_one({"device_id": device_id})
        if document is None:
            return None
        return DeviceResponse.model_validate(self._without_id(document))

    def update_status(
        self, device_id: str, status_update: StatusUpdate
    ) -> DeviceResponse | None:
        document = self._devices.find_one_and_update(
            {"device_id": device_id},
            {"$set": {"status": status_update.status}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return None
        return DeviceResponse.model_validate(self._without_id(document))

    def save_alert(self, alert: AlertResponse) -> AlertResponse:
        document = alert.model_dump()
        self._alerts.insert_one(document)
        return AlertResponse.model_validate(self._without_id(document))

    def list_alerts(self) -> list[AlertResponse]:
        return [
            AlertResponse.model_validate(self._without_id(document))
            for document in self._alerts.find({})
        ]