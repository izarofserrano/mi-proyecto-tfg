from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import verify_api_key
from app.api.routes import pipeline as pipeline_routes
from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401 — registers models with Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Traffic Summary API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    pipeline_routes.router,
    prefix="/api/v1/pipeline",
    tags=["pipeline"],
    dependencies=[Depends(verify_api_key)],
)
