from unittest.mock import Mock

from app.db import collections


def test_ensure_indexes_uses_configured_collections_and_stable_indexes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(collections, "DEVICES_COLLECTION", "net_devices")
    monkeypatch.setattr(collections, "ALERTS_COLLECTION", "net_alerts")
    devices = Mock()
    alerts = Mock()
    db = {"net_devices": devices, "net_alerts": alerts}

    collections.ensure_indexes(db)
    collections.ensure_indexes(db)

    assert devices.create_index.call_args_list == [
        (([("device_id", collections.ASCENDING)],), {"unique": True, "name": "uq_device_id"}),
        (([("device_id", collections.ASCENDING)],), {"unique": True, "name": "uq_device_id"}),
    ]
    assert alerts.create_index.call_args_list == [
        (([("device_id", collections.ASCENDING)],), {"name": "idx_alert_device_id"}),
        (([("timestamp", collections.ASCENDING)],), {"name": "idx_alert_timestamp"}),
        (([("device_id", collections.ASCENDING)],), {"name": "idx_alert_device_id"}),
        (([("timestamp", collections.ASCENDING)],), {"name": "idx_alert_timestamp"}),
    ]