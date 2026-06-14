"""Background task: build per-user daily digests as in-app notifications.

Notifications are delivered live over WebSocket during the day; this morning job
rolls up what each user missed (unread items from the last 24h) into a single
digest notification so nothing important is lost. Created via the notifications
service so cross-domain creation stays consistent.

Opens its own :class:`AsyncSession` (workers run outside the request lifecycle)
and commits at the boundary.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from app.core.db import SessionFactory
from app.core.logging import get_logger

log = get_logger(__name__)

# Roll up notifications created within this window into the morning digest.
_DIGEST_WINDOW_HOURS = 24
# Don't digest the digests we ourselves create.
_DIGEST_TYPE = "system"


async def send_daily_digests(ctx: dict[str, Any]) -> dict[str, int]:
    """Build one digest notification per user with unread activity in the window.

    Aggregates each user's unread notifications from the last
    ``_DIGEST_WINDOW_HOURS`` (excluding prior digests) and creates a single
    ``system`` digest notification summarising the count and the breakdown by
    type. Skips users with nothing to report.

    Returns ``{users, digests}`` for observability.
    """
    from app.domains.notifications import service as notifications_service
    from app.domains.notifications.models import Notification

    since = datetime.now(UTC) - timedelta(hours=_DIGEST_WINDOW_HOURS)
    users_seen = 0
    digests = 0

    async with SessionFactory() as session:
        # Unread, recent, non-digest notifications grouped by (user, type).
        grouped = (
            await session.execute(
                select(
                    Notification.user_id,
                    Notification.type,
                    func.count().label("n"),
                )
                .where(
                    Notification.is_read.is_(False),
                    Notification.created_at >= since,
                    Notification.type != _DIGEST_TYPE,
                )
                .group_by(Notification.user_id, Notification.type)
            )
        ).all()

        # Collapse into a per-user breakdown { user_id: {type: count} }.
        per_user: dict[Any, dict[str, int]] = {}
        for user_id, ntype, n in grouped:
            per_user.setdefault(user_id, {})[ntype] = int(n or 0)

        for user_id, breakdown in per_user.items():
            users_seen += 1
            total = sum(breakdown.values())
            if total <= 0:
                continue
            parts = ", ".join(
                f"{count} {ntype.replace('_', ' ')}" for ntype, count in sorted(breakdown.items())
            )
            await notifications_service.create_notification(
                session,
                user_id=user_id,
                type=_DIGEST_TYPE,
                title=f"Your daily digest: {total} update{'s' if total != 1 else ''}",
                body=f"While you were away: {parts}.",
                link="/notifications",
                payload={
                    "kind": "daily_digest",
                    "total": total,
                    "breakdown": breakdown,
                    "window_hours": _DIGEST_WINDOW_HOURS,
                    "generated_at": datetime.now(UTC).isoformat(),
                },
            )
            digests += 1

        await session.commit()

    log.info("workers.digests.sent", users=users_seen, digests=digests)
    return {"users": users_seen, "digests": digests}
