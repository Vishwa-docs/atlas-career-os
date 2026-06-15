"""Read/response schemas for explainable candidate↔job matching.

Every match carries its component sub-scores and a :class:`GlassBox` so the
"why" is rendered identically on both the candidate and the employer side.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel
from app.domains.ai.schemas import Citation, Confidence, GlassBox


class SubScores(BaseModel):
    """The transparent components blended into the overall match score."""

    semantic: float = Field(ge=0.0, le=1.0)
    skill_overlap: float = Field(ge=0.0, le=1.0)
    trajectory_fit: float = Field(ge=0.0, le=1.0)
    salary_fit: float = Field(ge=0.0, le=1.0)


class MatchExplanation(BaseModel):
    """The structured Glass Box an LLM fills, grounded in the sub-scores."""

    glass_box: GlassBox


class JobBrief(ORMModel):
    """Lightweight job projection returned in candidate-facing matches."""

    id: str
    title: str
    org_id: str
    location: str | None = None
    work_mode: str | None = None
    seniority: str | None = None
    comp_min: int | None = None
    comp_max: int | None = None
    currency: str = "MYR"


class CandidateSummary(BaseModel):
    """Consent-aware, minimal candidate projection for employer-facing matches."""

    id: str
    full_name: str
    headline: str | None = None
    current_role: str | None = None
    location: str | None = None
    years_experience: float = 0.0
    open_to_work: bool = True
    top_skills: list[str] = Field(default_factory=list)
    avatar_url: str | None = None
    consent_basis: str = Field(
        default="open_to_work",
        description="Why this candidate is visible: 'consent_grant' or 'open_to_work'.",
    )


class JobMatch(BaseModel):
    """A candidate's explained match against one job."""

    job: JobBrief
    score: float = Field(ge=0.0, le=1.0)
    sub_scores: SubScores
    glass_box: GlassBox


class CandidateMatch(BaseModel):
    """An employer's explained match against one candidate."""

    candidate_summary: CandidateSummary
    score: float = Field(ge=0.0, le=1.0)
    sub_scores: SubScores
    glass_box: GlassBox
    consent_note: str | None = None


__all__ = [
    "SubScores",
    "MatchExplanation",
    "JobBrief",
    "CandidateSummary",
    "JobMatch",
    "CandidateMatch",
    "Citation",
    "Confidence",
    "GlassBox",
]
