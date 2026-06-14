"""Pydantic v2 schemas for the candidate Navigator domain.

Read-schemas extend :class:`ORMModel` (``from_attributes=True``) so they
serialize straight from ORM rows. AI outputs (resume parse) embed a
:class:`GlassBox` per the platform trust contract.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel
from app.domains.ai.schemas import GlassBox

# --------------------------------------------------------------------------- #
# Profile
# --------------------------------------------------------------------------- #


class CandidateProfileRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    country: str = "MY"
    aspirations: str | None = None
    target_occupation_id: uuid.UUID | None = None
    current_occupation_id: uuid.UUID | None = None
    years_experience: float = 0.0
    open_to_work: bool = True
    completeness: int = 0
    links: dict = Field(default_factory=dict)


class CandidateProfileUpdate(BaseModel):
    headline: str | None = Field(default=None, max_length=200)
    summary: str | None = None
    location: str | None = Field(default=None, max_length=120)
    aspirations: str | None = None
    target_occupation_id: uuid.UUID | None = None
    years_experience: float | None = Field(default=None, ge=0.0, le=80.0)
    open_to_work: bool | None = None


# --------------------------------------------------------------------------- #
# Career events
# --------------------------------------------------------------------------- #


class CareerEventBase(BaseModel):
    type: str = Field(description="role | education | project | break | credential | achievement")
    title: str = Field(max_length=200)
    organization: str | None = Field(default=None, max_length=200)
    occupation_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    narrative: str | None = None
    highlights: list[str] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)
    break_reason: str | None = Field(default=None, max_length=40)


class CareerEventCreate(CareerEventBase):
    pass


class CareerEventUpdate(BaseModel):
    type: str | None = None
    title: str | None = Field(default=None, max_length=200)
    organization: str | None = Field(default=None, max_length=200)
    occupation_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    narrative: str | None = None
    highlights: list[str] | None = None
    skills_used: list[str] | None = None
    break_reason: str | None = Field(default=None, max_length=40)


class CareerEventRead(ORMModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    type: str
    title: str
    organization: str | None = None
    occupation_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    narrative: str | None = None
    highlights: list[str] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)
    break_reason: str | None = None


# --------------------------------------------------------------------------- #
# Skills
# --------------------------------------------------------------------------- #


class CandidateSkillRead(ORMModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    name: str | None = None
    slug: str | None = None
    proficiency: float = 0.5
    evidence_type: str = "asserted"
    confidence: float = 0.5
    years: float = 0.0


class SkillInput(BaseModel):
    """One skill the candidate asserts; resolved to the taxonomy by name/slug."""

    name: str = Field(max_length=160)
    proficiency: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_type: str = "asserted"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    years: float = Field(default=0.0, ge=0.0)


class SkillsReplace(BaseModel):
    """PUT body for the candidate skill set."""

    skills: list[SkillInput] = Field(default_factory=list)
    merge: bool = Field(
        default=False,
        description="If true, upsert into the existing set; else replace it.",
    )


# --------------------------------------------------------------------------- #
# /me composite + dashboard
# --------------------------------------------------------------------------- #


class CandidateMe(BaseModel):
    profile: CandidateProfileRead
    career_events: list[CareerEventRead] = Field(default_factory=list)
    skills: list[CandidateSkillRead] = Field(default_factory=list)
    completeness: int = 0


class DashboardStats(BaseModel):
    applications: int = 0
    matches: int = 0
    profile_completeness: int = 0
    market_percentile: int | None = None


class Nudge(BaseModel):
    title: str
    body: str
    type: str = "tip"


class MarketSnapshot(BaseModel):
    median_salary_myr: int | None = None
    demand_note: str = ""


class CandidateDashboard(BaseModel):
    stats: DashboardStats
    recent_matches: list[dict] = Field(default_factory=list)
    nudges: list[Nudge] = Field(default_factory=list)
    market_snapshot: MarketSnapshot


# --------------------------------------------------------------------------- #
# Resume parsing (AI preview — not committed)
# --------------------------------------------------------------------------- #


class ResumeRequest(BaseModel):
    text: str | None = None


class ParsedExperience(BaseModel):
    title: str
    organization: str | None = None
    start: str | None = None
    end: str | None = None
    highlights: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ParsedEducation(BaseModel):
    title: str
    organization: str | None = None
    year: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ParsedSkill(BaseModel):
    name: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ResumeParse(BaseModel):
    """Structured resume extraction with a Glass Box explaining the inference."""

    full_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    experiences: list[ParsedExperience] = Field(default_factory=list)
    education: list[ParsedEducation] = Field(default_factory=list)
    skills: list[ParsedSkill] = Field(default_factory=list)
    glass_box: GlassBox


# --------------------------------------------------------------------------- #
# Consent-trimmed public view (employer / university)
# --------------------------------------------------------------------------- #


class CandidatePublic(BaseModel):
    """What an external org sees, trimmed to the granted scopes."""

    id: uuid.UUID
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    country: str = "MY"
    years_experience: float = 0.0
    open_to_work: bool = True
    target_occupation_id: uuid.UUID | None = None
    current_occupation_id: uuid.UUID | None = None
    skills: list[CandidateSkillRead] = Field(default_factory=list)
    career_events: list[CareerEventRead] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
