"""ARQ worker configuration for Atlas background jobs.

Run with: ``arq app.workers.arq_settings.WorkerSettings``.

The worker shares the app's Redis (via ``settings.redis_url``) and runs three
scheduled jobs that keep the platform's derived data fresh outside the request
path:

* ``recompute_retention_signals`` — nightly at 02:00, raises quiet signals.
* ``send_daily_digests`` — every morning at 07:00, rolls up unread activity.
* ``reembed_stale`` — every 6 hours, backfills missing embeddings.

Each task opens its own ``AsyncSession`` (see the task modules), so the worker
itself only needs Redis configuration here.
"""

from __future__ import annotations

from typing import Any

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.workers.tasks.digests import send_daily_digests
from app.workers.tasks.embeddings import reembed_stale
from app.workers.tasks.signals import recompute_retention_signals

log = get_logger(__name__)


async def on_startup(ctx: dict[str, Any]) -> None:
    """Configure logging once when the worker process boots."""
    configure_logging()
    log.info("workers.startup", redis=settings.redis_url)


async def on_shutdown(ctx: dict[str, Any]) -> None:
    """Best-effort shutdown hook for symmetry/observability."""
    log.info("workers.shutdown")


class WorkerSettings:
    """ARQ ``WorkerSettings``: Redis connection, task registry, cron schedule."""

    redis_settings: RedisSettings = RedisSettings.from_dsn(settings.redis_url)

    # Tasks that can be enqueued on demand (e.g. by services).
    functions = [
        recompute_retention_signals,
        send_daily_digests,
        reembed_stale,
    ]

    # Scheduled jobs. ``run_at_startup=False`` keeps boots quiet; ``unique`` stops
    # overlapping runs of the same job across workers.
    cron_jobs = [
        cron(
            recompute_retention_signals,
            name="recompute_retention_signals",
            hour=2,
            minute=0,
            run_at_startup=False,
            unique=True,
        ),
        cron(
            send_daily_digests,
            name="send_daily_digests",
            hour=7,
            minute=0,
            run_at_startup=False,
            unique=True,
        ),
        cron(
            reembed_stale,
            name="reembed_stale",
            hour={0, 6, 12, 18},
            minute=0,
            run_at_startup=False,
            unique=True,
        ),
    ]

    on_startup = on_startup
    on_shutdown = on_shutdown
