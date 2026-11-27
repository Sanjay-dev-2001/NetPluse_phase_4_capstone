# NetPluse API

A small FastAPI modular monolith for managing network devices. Device and alert data is stored in MySQL.

Install dependencies with `python -m pip install -r requirements.txt`, then start the API with:

```bash
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `http://127.0.0.1:8000/docs`.

For database configuration, copy `.env.example` to `.env` and set the MySQL connection values. An optional `DATABASE_URL` overrides the individual settings and should use the `mysql+pymysql` driver.

Create the configured MySQL database and ensure the configured user has permission to create tables. From the project root, apply the migrations and inspect the applied revision and migration history:

```bash
python -m alembic upgrade head
python -m alembic current
python -m alembic history --verbose
```

Run the test suite with `python -m pytest -q`. Route tests use SQLite and the service dependency can be overridden with `InMemoryDeviceRepository` for isolated tests.

To also run the opt-in MySQL integration test, set `TEST_MYSQL_URL` to a `mysql+pymysql` URL for a migrated test database, then run `python -m pytest -q tests/test_mysql_device_repository.py`. The test removes the records it creates.