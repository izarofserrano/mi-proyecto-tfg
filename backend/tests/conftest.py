"""Fixtures shared by integration tests.

Uses an in-memory SQLite database so no PostgreSQL is required.
The engine and session factory are patched at module level so that
both the FastAPI dependency (get_db) and the background service
(execute_pipeline → AsyncSessionLocal) hit the same test DB.

Note: httpx.ASGITransport does NOT fire ASGI lifespan events, so
Base.metadata.create_all must be called explicitly here.
"""
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.session as db_session_module
import app.services.pipeline as pipeline_module
from app.db.base import Base
from app.main import app

_TEST_DB_URL = "sqlite+aiosqlite://"  # in-memory, shared via StaticPool


@pytest_asyncio.fixture
async def http_client(monkeypatch):
    """AsyncClient backed by a fresh in-memory SQLite DB.

    execute_pipeline is replaced with a no-op so tests focus on the HTTP
    contract without running the full heavy pipeline.
    """
    engine = create_async_engine(
        _TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Patch session module so get_db (dep injection) and pipeline service use test DB.
    monkeypatch.setattr(db_session_module, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(pipeline_module, "AsyncSessionLocal", session_factory)

    # Create tables manually — ASGITransport skips lifespan so create_all never runs.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Mock execute_pipeline — no-op keeps job in "pending" state during tests.
    async def _noop(*args, **kwargs):
        pass

    monkeypatch.setattr(pipeline_module, "execute_pipeline", _noop)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    await engine.dispose()
