"""Pydantic schemas for quiet signals."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.domains.ai.schemas import GlassBox
from app.domains.signals.models import SIGNAL_TYPES

_STATUSES = ("open", "acknowledged", "actioned", "dismissed")


class SignalEvidence(BaseModel):
    """One supporting evidence row rendered under a signal."""

    label: str
    detail: str | None = None


class SignalRead(BaseModel):
    """A signal with a human title, severity, structured evidence, and a Glass Box."""

    id: str
    type: str
    subject_candidate_id: str
    subject_name: str | None = None
    title: str
    summary: str | None = None
    severity: str | None = None  # low | medium | high
    status: str
    evidence: list[SignalEvidence] = Field(default_factory=list)
    glass_box: GlassBox
    detected_at: datetime | None = None


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
