"""Pydantic schemas for in-app notifications."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel


class NotificationRead(ORMModel):
    """A single notification as rendered in the bell/inbox."""

    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    title: str
    body: str | None = None
    link: str | None = None
    is_read: bool
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class MarkAllReadResult(BaseModel):
    """Outcome of marking every notification read."""

    updated: int
