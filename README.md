# NetPluse API

A small FastAPI modular monolith for managing network devices. Device data is held in memory and resets when the process restarts.

Install dependencies with `python -m pip install -r requirements.txt`, then start the API with:

```bash
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `http://127.0.0.1:8000/docs`.

For database configuration, copy `.env.example` to `.env` and set the MySQL connection values. An optional `DATABASE_URL` overrides the individual settings and should use the `mysql+pymysql` driver. The existing device API still stores data in memory.