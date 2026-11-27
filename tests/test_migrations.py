import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_alembic(database_url, *arguments):
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    environment["PYTHON_DOTENV_DISABLED"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )


def test_mysql_offline_migration_with_encoded_password():
    result = run_alembic(
        "mysql+pymysql://user:p%40ss@localhost/netpluse", "upgrade", "head", "--sql"
    )
    assert "CREATE TABLE devices" in result.stdout
    assert "CREATE TABLE alerts" in result.stdout
    assert "FOREIGN KEY(device_id) REFERENCES devices (device_id)" in result.stdout
    assert "ALTER TABLE devices ADD COLUMN location VARCHAR(255)" in result.stdout


def test_upgrade_metadata_and_downgrade(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    run_alembic(database_url, "upgrade", "0f31d72c49a1")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO devices (device_id, name, device_type, ip_address, status) "
                "VALUES (:device_id, :name, :device_type, :ip_address, :status)"
            ),
            {
                "device_id": "existing-device",
                "name": "Core Router",
                "device_type": "router",
                "ip_address": "192.0.2.1",
                "status": "online",
            },
        )

    run_alembic(database_url, "upgrade", "head")
    inspector = inspect(engine)
    assert {"alembic_version", "devices", "alerts"} <= set(inspector.get_table_names())
    assert inspector.get_foreign_keys("alerts")[0]["referred_table"] == "devices"
    location = next(column for column in inspector.get_columns("devices") if column["name"] == "location")
    assert location["nullable"] is True
    with engine.begin() as connection:
        record = connection.execute(text("SELECT name, status, location FROM devices")).one()
        assert tuple(record) == ("Core Router", "online", None)
        connection.execute(text("UPDATE devices SET location = 'Server Room'"))

    run_alembic(database_url, "downgrade", "0f31d72c49a1")
    assert "location" not in {column["name"] for column in inspect(engine).get_columns("devices")}
    with engine.connect() as connection:
        assert tuple(connection.execute(text("SELECT name, status FROM devices")).one()) == (
            "Core Router", "online"
        )

    run_alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        record = connection.execute(text("SELECT name, status, location FROM devices")).one()
        assert tuple(record) == ("Core Router", "online", None)
    assert "e74c23112244" in run_alembic(database_url, "current").stdout
    assert "0f31d72c49a1" in run_alembic(database_url, "history").stdout
    assert "e74c23112244" in run_alembic(database_url, "history").stdout
    assert "No new upgrade operations detected" in run_alembic(database_url, "check").stdout

    run_alembic(database_url, "downgrade", "base")
    assert "devices" not in inspect(engine).get_table_names()
    assert "alerts" not in inspect(engine).get_table_names()
    engine.dispose()