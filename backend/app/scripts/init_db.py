"""Create the schema for local/demo use.

Enables the pgvector extension and creates all tables via ``Base.metadata``.
Idempotent. For production-grade migrations use Alembic (``alembic upgrade head``)
— the environment is fully wired in ``alembic/env.py``; this script is the
zero-friction path for the demo stack.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.core.db import engine
from app.core.logging import configure_logging, get_logger
from app.db.base import Base
from app.db.registry import import_all_models

configure_logging()
log = get_logger(__name__)


async def init_db() -> None:
    import_all_models()
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    log.info("init_db.complete", tables=len(Base.metadata.tables))


if __name__ == "__main__":
    asyncio.run(init_db())
