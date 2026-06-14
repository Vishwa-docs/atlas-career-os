"""Skills & occupations taxonomy — the shared vocabulary of the Career Graph.

Seeded from O*NET / ESCO (CC-BY) with an ISCO-08 pivot to Malaysia's MASCO.
Occupation transitions give us the empirical "realistic next moves" graph.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Skill(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    # External identifiers for interoperability.
    onet_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    esco_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lightcast_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Market signal for Skill Half-Life: <0 means declining demand, >0 rising.
    demand_trend: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class Occupation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "occupations"

    title: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    isco_code: Mapped[str | None] = mapped_column(String(12), index=True, nullable=True)
    masco_code: Mapped[str | None] = mapped_column(String(12), index=True, nullable=True)
    onet_soc: Mapped[str | None] = mapped_column(String(12), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    family: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    typical_education: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Median monthly salary anchor (MYR) from OpenDOSM, when available.
    median_salary_myr: Mapped[int | None] = mapped_column(Integer, nullable=True)


class OccupationSkill(UUIDMixin, Base):
    __tablename__ = "occupation_skills"
    __table_args__ = (
        UniqueConstraint("occupation_id", "skill_id", name="uq_occupation_skills_occ_skill"),
    )

    occupation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    level: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    essential: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class OccupationTransition(UUIDMixin, Base):
    """A weighted edge in the job-transition graph: how often from→to happens."""

    __tablename__ = "occupation_transitions"
    __table_args__ = (
        UniqueConstraint("from_occupation_id", "to_occupation_id", name="uq_occ_transition_pair"),
    )

    from_occupation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    to_occupation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    weight: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    median_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    median_salary_delta_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
