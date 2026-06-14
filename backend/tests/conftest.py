"""Pytest fixtures: a real Postgres (pgvector) via testcontainers, an async
HTTP client bound to the app, and a mocked LLM.

We use a real Postgres (not SQLite) so pgvector, RLS, and JSONB behave exactly as
in production. The container is session-scoped (started once); the async engine
and sessions are function-scoped so they live on the same event loop as each test
(sharing async resources across loops triggers "attached to a different loop"
errors). Each request gets its own pooled session (the async-safe pattern), and
every table is truncated after each test. The LLM is always the deterministic
mock — tests never call a paid API.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture(scope="session")
def pg_url() -> Generator[str, None, None]:
    """Spin up a disposable Postgres with pgvector for the whole test session."""
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:  # pragma: no cover
        pytest.skip("testcontainers not installed")

    try:
        with PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg") as pg:
            yield pg.get_connection_url()
    except Exception as exc:  # pragma: no cover - Docker not available locally
        pytest.skip(f"Docker/Postgres unavailable: {exc}")


@pytest_asyncio.fixture
async def engine(pg_url: str):
    """Function-scoped async engine; ensures the schema exists (idempotent)."""
    from app.db.base import Base
    from app.db.registry import import_all_models

    import_all_models()
    eng = create_async_engine(pg_url, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    # Clean all rows so the next test starts empty (schema is reused).
    tables = ", ".join(f'"{t}"' for t in Base.metadata.tables)
    async with eng.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """A standalone session for tests that touch the DB directly."""
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    """App-bound async client. Each request gets its own pooled session."""
    from app.core.db import get_session
    from app.domains.ai.llm.factory import get_llm
    from app.domains.ai.llm.mock import MockLLMClient
    from app.main import app

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

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
