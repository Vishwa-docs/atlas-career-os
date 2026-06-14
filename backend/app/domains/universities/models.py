"""University-side entities: cohorts, graduate outcomes, internships.

These power the Outcomes Studio — decades-long outcome tracking, readiness, and
the internship marketplace. Outcomes link a candidate's evolving graph back to
the program that trained them.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Cohort(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cohorts"

    university_org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    program: Mapped[str] = mapped_column(String(200), nullable=False)
    faculty: Mapped[str | None] = mapped_column(String(160), nullable=True)
    graduation_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(40), default="bachelor", nullable=False)


class CohortStudent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cohort_students"
    __table_args__ = (
        UniqueConstraint("cohort_id", "candidate_id", name="uq_cohort_students_cohort_cand"),
    )

    cohort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cohorts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_ref: Mapped[str | None] = mapped_column(String(60), nullable=True)


class Outcome(UUIDMixin, TimestampMixin, Base):
    """A point-in-time graduate outcome record (captured repeatedly over decades)."""

    __tablename__ = "outcomes"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cohorts.id", ondelete="SET NULL"), index=True, nullable=True
    )
    captured_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    # employed | further_study | seeking | not_seeking | entrepreneur
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    role_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    employer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    salary_myr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    months_to_employment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    field_relevant: Mapped[bool | None] = mapped_column(nullable=True)


class Internship(UUIDMixin, TimestampMixin, Base):
    """Internship listings for the Live Internship Marketplace."""

    __tablename__ = "internships"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills_focus: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    grows_into: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stipend_myr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="open", nullable=False, index=True)
