"""Real-time notification delivery over WebSockets.

A process-local :class:`ConnectionManager` keyed by ``user_id`` pushes events to
every socket a user has open. This is correct and complete for a single-instance
deployment (e.g. the hackathon demo / Render free tier).

Scale-out path (documented, not required for the demo): publish each event to a
Redis pub/sub channel and run one subscriber per instance that fans out to its
local sockets — the Redis dependency is already wired for ARQ. The publish hook
below is deliberately best-effort and non-transactional: the client treats a
push as a hint and refetches the authoritative list over REST, so a rolled-back
notification can never leave stale state on screen.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger

log = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[user_id].add(websocket)
        log.info("ws.connect", user_id=user_id, total=len(self._connections[user_id]))

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.get(user_id, set()).discard(websocket)
            if not self._connections.get(user_id):
                self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> None:
        """Deliver ``message`` to all of the user's open sockets (best-effort)."""
        sockets = list(self._connections.get(user_id, ()))
        if not sockets:
            return
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:  # pragma: no cover - client vanished mid-send
                dead.append(ws)
        for ws in dead:
            await self.disconnect(user_id, ws)

    def connection_count(self) -> int:
        return sum(len(s) for s in self._connections.values())


# Process-wide singleton used by the router and by create_notification().
manager = ConnectionManager()


async def publish_notification(user_id: str, payload: dict[str, Any]) -> None:
    """Fire-and-forget push of a freshly created notification."""
    try:
        await manager.send_to_user(user_id, {"type": "notification", **payload})
    except Exception:  # pragma: no cover - never let realtime break the request
        log.warning("ws.publish_failed", user_id=user_id)
