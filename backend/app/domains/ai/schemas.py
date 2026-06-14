"""Glass Box schemas — the trust contract for every AI output in Atlas.

Ben's brief is explicit: "No black-box scores, no false precision." So *every*
AI verdict the platform produces is wrapped in a :class:`GlassBox` envelope that
explains the reasoning in human language, cites its evidence, states a confidence
band, and says what would change the conclusion. The frontend renders this
uniformly so users always see the "why".
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CitationSourceType(StrEnum):
    CAREER_HISTORY = "career_history"
    JOB_POSTING = "job_posting"
    SALARY_DATA = "salary_data"
    SKILL_TAXONOMY = "skill_taxonomy"
    LABOR_MARKET = "labor_market"
    COHORT_DATA = "cohort_data"
    DEMOGRAPHIC_DATA = "demographic_data"
    USER_INPUT = "user_input"


class Citation(BaseModel):
    """A single piece of grounding evidence behind an AI statement."""

    label: str = Field(description="Short human-readable label, e.g. 'DOSM 3Q2025 wages'.")
    source_type: CitationSourceType
    source_id: str | None = Field(default=None, description="Internal id of the cited record.")
    snippet: str | None = Field(default=None, description="The exact supporting text/figure.")
    url: str | None = None


class GlassBox(BaseModel):
    """The explainability envelope attached to every AI judgement."""

    rationale: str = Field(description="Plain-language explanation a human can follow.")
    confidence: Confidence
    confidence_score: float = Field(ge=0.0, le=1.0, description="Calibrated 0–1 estimate.")
    citations: list[Citation] = Field(default_factory=list)
    what_would_change_this: list[str] = Field(
        default_factory=list,
        description="Concrete factors that would raise/lower this conclusion.",
    )
    caveats: list[str] = Field(
        default_factory=list, description="Known limitations / where uncertainty sits."
    )


class AIResponse(BaseModel):
    """Generic structured-output base: a typed payload + its Glass Box."""

    glass_box: GlassBox
