"""Async database engine and session management.

The :func:`get_session` dependency yields a request-scoped ``AsyncSession`` and,
when an actor context is present, sets Postgres GUCs (``app.current_user_id`` /
``app.current_org_id``) so Row-Level-Security policies can enforce tenant
isolation as a defence-in-depth backstop behind app-layer scoping.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextvars import ContextVar

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Actor context (populated by auth dependency) for RLS GUCs + audit logging.
current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)
current_org_id: ContextVar[str | None] = ContextVar("current_org_id", default=None)

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
)

SessionFactory = async_sessionmaker(
    bind=engine, expire_on_commit=False, autoflush=False, class_=AsyncSession
)


async def _apply_rls_context(session: AsyncSession) -> None:
    """Set per-request GUCs for RLS. Safe no-op on non-Postgres backends."""
    uid = current_user_id.get()
    oid = current_org_id.get()
    if uid is None and oid is None:
        return
    try:
        await session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": uid or ""},
        )
        await session.execute(
            text("SELECT set_config('app.current_org_id', :oid, true)"),
            {"oid": oid or ""},
        )
    except Exception:  # pragma: no cover - backend without set_config (e.g. sqlite)
        pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: a transactional, request-scoped session.

    Commit happens at the service boundary; we roll back on any unhandled error.
    """
    async with SessionFactory() as session:
        await _apply_rls_context(session)
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
