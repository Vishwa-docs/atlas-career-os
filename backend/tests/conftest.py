"""Pytest fixtures: a real Postgres (pgvector) via testcontainers, an async
HTTP client bound to the app, and a mocked LLM.

We use a real Postgres (not SQLite) so pgvector, RLS, and JSONB behave exactly as
in production. Each test runs inside a transaction that is rolled back, keeping
tests isolated and fast. The LLM is always the deterministic mock — tests never
call a paid API.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def pg_url() -> Generator[str, None, None]:
    """Spin up a disposable Postgres with pgvector for the whole test session."""
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg") as pg:
        yield pg.get_connection_url()


@pytest_asyncio.fixture(scope="session")
async def engine(pg_url: str):
    from app.db.base import Base
    from app.db.registry import import_all_models

    import_all_models()
    eng = create_async_engine(pg_url, poolclass=None)
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """A transactional session rolled back after each test."""
    connection = await engine.connect()
    trans = await connection.begin()
    factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """App-bound async client with DB + LLM dependencies overridden."""
    from app.core.db import get_session
    from app.domains.ai.llm.factory import get_llm
    from app.domains.ai.llm.mock import MockLLMClient
    from app.main import app

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_llm] = lambda: MockLLMClient()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm() -> object:
    from app.domains.ai.llm.mock import MockLLMClient

    return MockLLMClient()
