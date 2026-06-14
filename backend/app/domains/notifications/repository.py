"""All DB queries for notifications (async SQLAlchemy 2.0)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.models import Notification


async def add(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
    payload: dict[str, Any] | None = None,
) -> Notification:
    """Insert a new notification (flushed so the caller gets its id)."""
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        link=link,
        payload=payload or {},
    )
    session.add(notif)
    await session.flush()
    return notif


async def list_for_user(
    session: AsyncSession, *, user_id: uuid.UUID, offset: int, limit: int
) -> tuple[list[Notification], int]:
    """Return a page of notifications (newest first) and the total count."""
    base = select(Notification).where(Notification.user_id == user_id)
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    rows = await session.scalars(
        base.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
    )
    return list(rows), int(total or 0)


async def get_owned(
    session: AsyncSession, *, notification_id: uuid.UUID, user_id: uuid.UUID
) -> Notification | None:
    """Fetch one notification, scoped to its owner (BOLA defence)."""
    return await session.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
    )


async def mark_all_read(session: AsyncSession, *, user_id: uuid.UUID) -> int:
    """Mark every unread notification for a user as read; return the count."""
    result = await session.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    return int(result.rowcount or 0)
