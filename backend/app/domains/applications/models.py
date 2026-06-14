"""Applications and their status timeline (the feedback loop both sides see)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin

# Canonical pipeline stages.
APPLICATION_STATUSES = (
    "applied",
    "screening",
    "shortlisted",
    "interview",
    "offer",
    "hired",
    "rejected",
    "withdrawn",
)


class Application(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id", name="uq_applications_cand_job"),)

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="applied", nullable=False, index=True)
    cover_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Feedback closes the loop for the candidate.
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="atlas", nullable=False)


class ApplicationEvent(UUIDMixin, TimestampMixin, Base):
    """Immutable status-change events for an application timeline."""

    __tablename__ = "application_events"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
