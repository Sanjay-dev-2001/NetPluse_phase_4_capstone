import importlib

import pytest
from sqlalchemy.engine import make_url

from app import config
from app.db import session


def test_mysql_settings_build_url_with_special_characters(monkeypatch):
    with monkeypatch.context() as environment:
        environment.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
        environment.delenv("DATABASE_URL", raising=False)
        environment.setenv("MYSQL_HOST", "db.example.com")
        environment.setenv("MYSQL_PORT", "3307")
        environment.setenv("MYSQL_DATABASE", "devices")
        environment.setenv("MYSQL_USER", "service")
        environment.setenv("MYSQL_PASSWORD", "p@ss:/word")
        importlib.reload(config)
        url = make_url(config.DATABASE_URL)
        assert url.drivername == "mysql+pymysql"
        assert (url.host, url.port, url.database) == ("db.example.com", 3307, "devices")
        assert (url.username, url.password) == ("service", "p@ss:/word")
    importlib.reload(config)


def test_database_url_override(monkeypatch):
    with monkeypatch.context() as environment:
        environment.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
        environment.setenv("DATABASE_URL", "mysql+pymysql://user:pass@db/other")
        importlib.reload(config)
        assert config.DATABASE_URL == "mysql+pymysql://user:pass@db/other"
    importlib.reload(config)


@pytest.mark.parametrize("raise_error", [False, True])
def test_get_db_closes_session(monkeypatch, raise_error):
    class FakeSession:
        closed = False

        def close(self):
            self.closed = True

    db = FakeSession()
    monkeypatch.setattr(session, "SessionLocal", lambda: db)
    dependency = session.get_db()
    assert next(dependency) is db
    if raise_error:
        with pytest.raises(ValueError):
            dependency.throw(ValueError("failure"))
    else:
        with pytest.raises(StopIteration):
            next(dependency)
    assert db.closed