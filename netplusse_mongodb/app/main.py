from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.collections import ensure_indexes
from app.db.mongo import get_db
from app.routes.devices import router as devices_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
	ensure_indexes(get_db())
	yield


app = FastAPI(title="NetPulse API", lifespan=lifespan)
app.include_router(devices_router)