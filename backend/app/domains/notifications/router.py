"""Thin HTTP + WebSocket layer for notifications."""

from __future__ import annotations

import uuid

import jwt
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_current_principal, get_session
from app.core.schemas import Page, PageParams
from app.core.security import decode_token
from app.domains.notifications import service
from app.domains.notifications.schemas import MarkAllReadResult, NotificationRead
from app.domains.notifications.ws import manager

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.websocket("/ws")
async def notifications_ws(websocket: WebSocket, token: str = Query(...)) -> None:
    """Authenticated real-time channel. The access token is passed as a query
    param (browsers can't set headers on a WebSocket handshake). Pushes a
    ``{type: "notification", ...}`` frame whenever a notification is created."""
    try:
        payload = decode_token(token, expected_type="access")
        user_id = payload["sub"]
    except (jwt.PyJWTError, KeyError):
        await websocket.close(code=4401)
        return

    await manager.connect(user_id, websocket)
    try:
        await websocket.send_json({"type": "connected"})
        while True:
            # We don't expect client messages; receiving lets us detect close.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(user_id, websocket)
    except Exception:  # pragma: no cover - defensive
        await manager.disconnect(user_id, websocket)


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
