"""The candidate side of the Career Graph: profile, career timeline, skills."""

from __future__ import annotations

import uuid
from datetime import date

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.base import Base, TimestampMixin, UUIDMixin

EMBED_DIM = settings.embedding_dimensions


class CandidateProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    headline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str] = mapped_column(String(2), default="MY", nullable=False)
    # Where the candidate is trying to go — drives trajectory-aware matching.
    aspirations: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_occupation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("occupations.id", ondelete="SET NULL"), nullable=True
    )
    current_occupation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("occupations.id", ondelete="SET NULL"), nullable=True
    )
    years_experience: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    open_to_work: Mapped[bool] = mapped_column(default=True, nullable=False)
    completeness: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Aggregate semantic embedding of the profile, for matching/similarity.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM), nullable=True)
    links: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class CareerEvent(UUIDMixin, TimestampMixin, Base):
    """A node on the 40-year arc: a role, study, project, break, or credential."""

    __tablename__ = "career_events"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # role | education | project | break | credential | achievement
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    occupation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("occupations.id", ondelete="SET NULL"), nullable=True
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(default=False, nullable=False)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    highlights: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    skills_used: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    # break reason (caregiving/health/study/sabbatical) for the Life Chapter Designer.
    break_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)


class CandidateSkill(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (
        UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skills_cand_skill"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    proficiency: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    # asserted | verified | inferred
    evidence_type: Mapped[str] = mapped_column(String(20), default="asserted", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    years: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
