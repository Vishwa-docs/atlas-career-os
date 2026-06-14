"""Quiet signals — the substrate for Retention, Onboarding, and Coach nudges.

Signals are observed, consented events (activity drop, peer departures, profile
updates, plateau, underpaid) that let managers/candidates act *before* the
resignation letter lands. Always explainable, never punitive.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin

SIGNAL_TYPES = (
    "activity_drop",
    "peer_departure",
    "profile_update",
    "underpaid",
    "plateau",
    "onboarding_risk",
    "open_role_fit",
    "skill_decay",
)


class Signal(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "signals"

    # The subject is a candidate (career-side) — observed within an org context when relevant.
    subject_candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=True
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    strength: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # open | acknowledged | actioned | dismissed
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
