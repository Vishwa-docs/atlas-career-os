"""Job postings — the employer side of the marketplace."""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.base import Base, TimestampMixin, UUIDMixin

EMBED_DIM = settings.embedding_dimensions


class Job(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "jobs"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    posted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    occupation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("occupations.id", ondelete="SET NULL"), index=True, nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    requirements: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    skills_required: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    # onsite | hybrid | remote
    work_mode: Mapped[str] = mapped_column(String(20), default="onsite", nullable=False)
    # internship | entry | mid | senior | lead | executive
    seniority: Mapped[str] = mapped_column(String(20), default="mid", nullable=False, index=True)
    employment_type: Mapped[str] = mapped_column(String(20), default="full_time", nullable=False)
    comp_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comp_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="MYR", nullable=False)
    # draft | open | closed
    status: Mapped[str] = mapped_column(String(12), default="open", nullable=False, index=True)
    is_internship: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Where this role can lead — used for trajectory-aware matching.
    growth_into: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
