from pymongo import ASCENDING
from pymongo.database import Database

from app.config import ALERTS_COLLECTION, DEVICES_COLLECTION


def ensure_indexes(db: Database) -> None:
    db[DEVICES_COLLECTION].create_index(
        [("device_id", ASCENDING)],
        unique=True,
        name="uq_device_id",
    )
    db[ALERTS_COLLECTION].create_index(
        [("device_id", ASCENDING)],
        name="idx_alert_device_id",
    )
    db[ALERTS_COLLECTION].create_index(
        [("timestamp", ASCENDING)],
        name="idx_alert_timestamp",
    )