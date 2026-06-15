"""Notification business logic + a public ``create_notification`` helper.

Other domains import :func:`create_notification` to fan out in-app alerts
(matches, applications, signals, consent). It flushes (not commits) so it can
participate in the caller's transaction; the caller commits at its boundary.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.schemas import Page
from app.domains.notifications import repository as repo
from app.domains.notifications.models import Notification
from app.domains.notifications.schemas import MarkAllReadResult, NotificationRead
from app.domains.notifications.ws import publish_notification


async def create_notification(
    session: AsyncSession,
    *,
    user_id: str | uuid.UUID,
    type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
    payload: dict[str, Any] | None = None,
) -> Notification:
    """Create an in-app notification for a user. Flushes, does not commit.

    Exported for cross-domain use; callers own the surrounding transaction.
    Also pushes a best-effort real-time frame to any open WebSocket; the client
    treats it as a hint and refetches the authoritative list over REST.
    """
    notif = await repo.add(
        session,
        user_id=uuid.UUID(str(user_id)),
        type=type,
        title=title,
        body=body,
        link=link,
        payload=payload,
    )
    await publish_notification(
        str(user_id),
        {"id": str(notif.id), "title": title, "body": body, "link": link, "kind": type},
    )
    return notif


async def list_notifications(
    session: AsyncSession, *, user_id: str, offset: int, limit: int, page: int, page_size: int
) -> Page[NotificationRead]:
    """Return the current user's notifications, newest first."""
    rows, total = await repo.list_for_user(
        session, user_id=uuid.UUID(user_id), offset=offset, limit=limit
    )
    return Page[NotificationRead](
        items=[NotificationRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def mark_read(
    session: AsyncSession, *, notification_id: uuid.UUID, user_id: str
) -> NotificationRead:
    """Mark a single owned notification read."""
    notif = await repo.get_owned(
        session, notification_id=notification_id, user_id=uuid.UUID(user_id)
    )
    if notif is None:
        raise NotFoundError("Notification not found.")
    notif.is_read = True
    await session.commit()
    await session.refresh(notif)
    return NotificationRead.model_validate(notif)


async def mark_all_read(session: AsyncSession, *, user_id: str) -> MarkAllReadResult:
    """Mark all of the user's notifications read."""
    updated = await repo.mark_all_read(session, user_id=uuid.UUID(user_id))
    await session.commit()
    return MarkAllReadResult(updated=updated)
