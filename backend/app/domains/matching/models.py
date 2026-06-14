"""Cached, explainable match results between candidates and jobs.

Every match carries its Glass Box (rationale + citations + confidence) as JSONB
so the "why" is persisted, auditable, and rendered identically on both sides.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class MatchResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "match_results"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_match_results_cand_job"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    # Component sub-scores for transparency.
    semantic_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    skill_overlap: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trajectory_fit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    salary_fit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # The Glass Box envelope (rationale, confidence, citations, ...).
    glass_box: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), default="v1", nullable=False)
