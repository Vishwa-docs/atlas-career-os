"""Pydantic schemas for quiet signals."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.schemas import ORMModel
from app.domains.signals.models import SIGNAL_TYPES

_STATUSES = ("open", "acknowledged", "actioned", "dismissed")


class SignalRead(ORMModel):
    """A signal with its supporting evidence."""

    id: uuid.UUID
    subject_candidate_id: uuid.UUID
    org_id: uuid.UUID | None = None
    type: str
    strength: float
    summary: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    status: str
    created_at: datetime


class SignalStatusUpdate(BaseModel):
    """Transition a signal to a new lifecycle status."""

    status: str

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str) -> str:
        if v not in _STATUSES:
            raise ValueError(f"status must be one of {_STATUSES}")
        return v


def is_valid_type(value: str) -> bool:
    """Whether ``value`` is a recognised signal type."""
    return value in SIGNAL_TYPES


def is_valid_status(value: str) -> bool:
    """Whether ``value`` is a recognised signal status."""
    return value in _STATUSES
