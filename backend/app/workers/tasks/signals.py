"""Background task: recompute quiet retention signals from recent activity.

Quiet signals (activity_drop, plateau, ...) let managers/candidates act *before*
the resignation letter lands. This nightly job scans recent application activity
and raises low-noise ``activity_drop`` signals for candidates who have gone quiet,
upserting them through the signals service so the same validation/exports apply.

Each run opens its own :class:`AsyncSession` (workers are outside the request
lifecycle, so there is no FastAPI-managed session) and commits at the boundary.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from app.core.db import SessionFactory
from app.core.logging import get_logger

log = get_logger(__name__)

# A candidate whose most recent application activity predates this window is
# considered to have "gone quiet" — a soft, explainable retention signal.
_QUIET_AFTER_DAYS = 30
# Don't re-raise the same signal type if one is already open for the subject.
_DEDUPE_OPEN = True


async def recompute_retention_signals(ctx: dict[str, Any]) -> dict[str, int]:
    """Scan recent activity and upsert ``activity_drop`` signals.

    Looks at every candidate that has applications, finds their latest activity,
    and raises an ``activity_drop`` signal (via the signals service) for those
    whose last activity is older than the quiet window. Idempotent per run: skips
    candidates that already have an open ``activity_drop`` signal.

    Returns a small summary dict ``{scanned, raised}`` for observability.
    """
    from app.domains.applications.models import Application
    from app.domains.signals import service as signals_service
    from app.domains.signals.models import Signal

    cutoff = datetime.now(UTC) - timedelta(days=_QUIET_AFTER_DAYS)
    scanned = 0
    raised = 0

    async with SessionFactory() as session:
        # Latest application activity per candidate.
        last_activity = (
            select(
                Application.candidate_id.label("candidate_id"),
                func.max(Application.updated_at).label("last_at"),
                func.count().label("application_count"),
            )
            .group_by(Application.candidate_id)
            .subquery()
        )
        rows = (
            await session.execute(
                select(
                    last_activity.c.candidate_id,
                    last_activity.c.last_at,
                    last_activity.c.application_count,
                ).where(last_activity.c.last_at < cutoff)
            )
        ).all()

        for candidate_id, last_at, application_count in rows:
            scanned += 1

            if _DEDUPE_OPEN:
                existing = await session.scalar(
                    select(Signal.id).where(
                        Signal.subject_candidate_id == candidate_id,
                        Signal.type == "activity_drop",
                        Signal.status == "open",
                    )
                )
                if existing is not None:
                    continue

            quiet_days = (datetime.now(UTC) - last_at).days if last_at else None
            # Longer silence → stronger (but capped) signal.
            strength = min(1.0, 0.4 + (quiet_days or 0) / 120.0)
            await signals_service.create_signal(
                session,
                subject_candidate_id=candidate_id,
                type="activity_drop",
                strength=strength,
                summary=(
                    f"No application activity for ~{quiet_days} days "
                    f"(last seen {last_at:%Y-%m-%d})."
                    if last_at
                    else "No recent application activity observed."
                ),
                evidence={
                    "last_activity_at": last_at.isoformat() if last_at else None,
                    "quiet_days": quiet_days,
                    "application_count": int(application_count or 0),
                    "window_days": _QUIET_AFTER_DAYS,
                    "computed_by": "workers.recompute_retention_signals",
                },
            )
            raised += 1

        await session.commit()

    log.info("workers.signals.recomputed", scanned=scanned, raised=raised)
    return {"scanned": scanned, "raised": raised}
