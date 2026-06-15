"""University Outcomes Studio schemas (org-scoped).

Powers the outcomes dashboard, graduate-outcome analytics, the student roster
with readiness scores, the Adaptive Readiness Profile, the Future-State
Curriculum gap analysis, and the internship marketplace. AI verdicts embed a
:class:`GlassBox`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel
from app.domains.ai.schemas import GlassBox

# --------------------------------------------------------------------------- #
# Dashboard & outcomes analytics
# --------------------------------------------------------------------------- #


class TrendPoint(BaseModel):
    year: int
    employment_rate: float
    median_salary: int | None = None


class UniversityDashboard(BaseModel):
    employment_rate: float = 0.0
    median_salary: int | None = None
    median_months_to_employ: float | None = None
    active_students: int = 0
    graduates_tracked: int = 0
    programs: int = 0
    internships_open: int = 0
    credentials_issued: int = 0
    currency: str = "MYR"
    trend: list[TrendPoint] = Field(default_factory=list)


class FieldRate(BaseModel):
    field: str
    employment_rate: float
    median_salary: int | None = None
    graduates: int | None = None


class OutcomesReport(BaseModel):
    employment_rate: float = 0.0
    median_salary: int | None = None
    median_months_to_employ: float | None = None
    currency: str = "MYR"
    by_field: list[FieldRate] = Field(default_factory=list)
    trend: list[TrendPoint] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Student roster & readiness
# --------------------------------------------------------------------------- #


class StudentRosterEntry(BaseModel):
    id: str
    full_name: str
    student_ref: str | None = None
    headline: str | None = None
    program: str | None = None
    field: str | None = None
    year: int | None = None
    cohort: str | None = None
    readiness_score: float = Field(ge=0.0, le=1.0)


class StudentRoster(BaseModel):
    items: list[StudentRosterEntry] = Field(default_factory=list)


class ReadinessDimension(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=1.0)
    benchmark: float | None = None
    detail: str | None = None


class ReadinessProfile(BaseModel):
    candidate_id: str | None = None
    student_name: str | None = None
    program: str | None = None
    score: float = Field(ge=0.0, le=1.0)
    dimensions: list[ReadinessDimension] = Field(default_factory=list)
    glass_box: GlassBox


# --------------------------------------------------------------------------- #
# Future-State Curriculum
# --------------------------------------------------------------------------- #


class MarketSkill(BaseModel):
    skill: str
    demand: float
    coverage: float = 0.0


class CurriculumGap(BaseModel):
    skill: str
    demand: float | None = None
    severity: str | None = None  # low | medium | high
    recommendation: str | None = None


class CurriculumReport(BaseModel):
    program: str
    market_skills: list[MarketSkill] = Field(default_factory=list)
    covered: list[str] = Field(default_factory=list)
    gaps: list[CurriculumGap] = Field(default_factory=list)
    glass_box: GlassBox


# --------------------------------------------------------------------------- #
# Internship marketplace
# --------------------------------------------------------------------------- #


class InternshipCreate(BaseModel):
    title: str
    description: str | None = None
    skills_focus: list[str] = Field(default_factory=list)
    grows_into: list[str] = Field(default_factory=list)
    location: str | None = None
    duration_months: int | None = None
    stipend_myr: int | None = None
    status: str = "open"


class InternshipRead(ORMModel):
    id: str
    org_id: str
    title: str
    description: str | None = None
    skills_focus: list[str] = Field(default_factory=list)
    grows_into: list[str] = Field(default_factory=list)
    location: str | None = None
    duration_months: int | None = None
    stipend_myr: int | None = None
    status: str
