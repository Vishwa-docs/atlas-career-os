"""Thin HTTP layer for notifications."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_current_principal, get_session
from app.core.schemas import Page, PageParams
from app.domains.notifications import service
from app.domains.notifications.schemas import MarkAllReadResult, NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationRead])
async def list_notifications(
    params: PageParams = Depends(PageParams),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> Page[NotificationRead]:
    """List the current user's notifications, newest first."""
    return await service.list_notifications(
        session,
        user_id=principal.user_id,
        offset=params.offset,
        limit=params.limit,
        page=params.page,
        page_size=params.page_size,
    )


@router.patch("/read-all", response_model=MarkAllReadResult)
async def mark_all_read(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> MarkAllReadResult:
    """Mark all of the current user's notifications read."""
    return await service.mark_all_read(session, user_id=principal.user_id)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: str,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> NotificationRead:
    """Mark a single notification read (ownership-checked)."""
    return await service.mark_read(
        session, notification_id=uuid.UUID(notification_id), user_id=principal.user_id
    )
