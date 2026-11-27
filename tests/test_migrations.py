import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, inspect


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_alembic(database_url, *arguments):
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
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


def test_upgrade_metadata_and_downgrade(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    run_alembic(database_url, "upgrade", "head")
    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert {"alembic_version", "devices", "alerts"} <= set(inspector.get_table_names())
    assert inspector.get_foreign_keys("alerts")[0]["referred_table"] == "devices"
    assert "0f31d72c49a1" in run_alembic(database_url, "current").stdout
    assert "0f31d72c49a1" in run_alembic(database_url, "history").stdout
    assert "No new upgrade operations detected" in run_alembic(database_url, "check").stdout

    run_alembic(database_url, "downgrade", "base")
    assert "devices" not in inspect(engine).get_table_names()
    assert "alerts" not in inspect(engine).get_table_names()
    engine.dispose()