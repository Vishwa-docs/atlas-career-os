"""Pydantic v2 schemas for the jobs domain (postings, search, match, debias)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel
from app.domains.ai.schemas import GlassBox


class JobBase(BaseModel):
    """Shared writable fields for a job posting."""

    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=1)
    occupation_id: uuid.UUID | None = None
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    skills_required: list[str] = Field(default_factory=list)
    location: str | None = None
    work_mode: str = "onsite"
    seniority: str = "mid"
    employment_type: str = "full_time"
    comp_min: int | None = None
    comp_max: int | None = None
    currency: str = "MYR"
    is_internship: bool = False
    growth_into: list[str] = Field(default_factory=list)
    closes_at: datetime | None = None


class JobCreate(JobBase):
    """Payload to create a job (org inferred from the principal)."""


class JobUpdate(BaseModel):
    """Partial update — every field optional."""

    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    occupation_id: uuid.UUID | None = None
    responsibilities: list[str] | None = None
    requirements: list[str] | None = None
    skills_required: list[str] | None = None
    location: str | None = None
    work_mode: str | None = None
    seniority: str | None = None
    employment_type: str | None = None
    comp_min: int | None = None
    comp_max: int | None = None
    currency: str | None = None
    status: str | None = None
    is_internship: bool | None = None
    growth_into: list[str] | None = None
    closes_at: datetime | None = None


class JobRead(ORMModel):
    """Public read view of a job posting."""

    id: uuid.UUID
    org_id: uuid.UUID
    posted_by: uuid.UUID | None = None
    title: str
    occupation_id: uuid.UUID | None = None
    description: str
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    skills_required: list[str] = Field(default_factory=list)
    location: str | None = None
    work_mode: str
    seniority: str
    employment_type: str
    comp_min: int | None = None
    comp_max: int | None = None
    currency: str
    status: str
    is_internship: bool
    growth_into: list[str] = Field(default_factory=list)
    views: int
    closes_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MatchSubScores(BaseModel):
    """The transparent component scores behind a blended match."""

    semantic: float = Field(ge=0.0, le=1.0)
    skill_overlap: float = Field(ge=0.0, le=1.0)
    trajectory_fit: float = Field(ge=0.0, le=1.0)
    salary_fit: float = Field(ge=0.0, le=1.0)


class JobMatchRead(BaseModel):
    """A candidate's explained match against one job."""

    score: float = Field(ge=0.0, le=1.0)
    sub_scores: MatchSubScores
    glass_box: GlassBox


class DebiasIssue(BaseModel):
    """One flagged biased/exclusionary phrase and how to fix it."""

    phrase: str
    why: str
    suggestion: str


class JobDebiasResult(BaseModel):
    """Bias Auditor output: a rewritten JD plus the issues found."""

    rewritten: str
    issues: list[DebiasIssue] = Field(default_factory=list)
    glass_box: GlassBox
