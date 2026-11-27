from datetime import datetime

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateIndex, CreateTable

from app.db.models import Alert, Device
from app.db.session import Base


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def make_device():
    return Device(
        device_id="router-01",
        name="Core Router",
        device_type="router",
        ip_address="192.168.1.1",
    )


def test_mysql_table_and_index_ddl_compiles():
    dialect = mysql.dialect()
    device_ddl = str(CreateTable(Device.__table__).compile(dialect=dialect))
    alert_ddl = str(CreateTable(Alert.__table__).compile(dialect=dialect))
    indexes = [
        str(CreateIndex(index).compile(dialect=dialect))
        for index in Device.__table__.indexes
    ]
    assert "PRIMARY KEY (device_id)" in device_ddl
    assert "FOREIGN KEY(device_id) REFERENCES devices (device_id)" in alert_ddl
    assert any("(device_id)" in index for index in indexes)


def test_device_and_alert_tables_and_timestamps(db_engine):
    indexes = inspect(db_engine).get_indexes("devices")
    assert any(index["column_names"] == ["device_id"] for index in indexes)

    with Session(db_engine) as db:
        device = make_device()
        db.add(device)
        db.commit()
        assert device.status == "online"
        assert isinstance(device.created_at, datetime)
        assert isinstance(device.updated_at, datetime)

        device.updated_at = datetime(2000, 1, 1)
        db.commit()
        device.status = "offline"
        db.commit()
        assert device.updated_at > datetime(2000, 1, 1)

        alert = Alert(device_id=device.device_id, message="Device offline")
        db.add(alert)
        db.commit()
        assert alert.id is not None
        assert isinstance(alert.timestamp, datetime)


def test_device_id_is_unique(db_engine):
    with Session(db_engine) as db:
        db.add(make_device())
        db.commit()
        db.add(make_device())
        with pytest.raises(IntegrityError):
            db.commit()


def test_alert_requires_existing_device(db_engine):
    with Session(db_engine) as db:
        db.add(Alert(device_id="missing", message="Device offline"))
        with pytest.raises(IntegrityError):
            db.commit()