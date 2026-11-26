# NetPluse API

A small FastAPI modular monolith for managing network devices. Device data is held in memory and resets when the process restarts.

Install dependencies with `python -m pip install -r requirements.txt`, then start the API with:

```bash
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `http://127.0.0.1:8000/docs`.