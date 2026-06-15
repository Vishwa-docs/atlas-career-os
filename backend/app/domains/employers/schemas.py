"""Employer analytics & dashboard schemas (org-scoped).

These power the employer cockpit: the hiring dashboard, the Onboarding Success
Predictor, the warm-bench re-engagement list, and the Workforce Resilience view.
Every AI verdict embeds a :class:`GlassBox` per Atlas's trust contract.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domains.ai.schemas import GlassBox

# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #


class PipelineStage(BaseModel):
    """Applicant count for one pipeline stage (ordered funnel item)."""

    stage: str
    count: int = 0


class RecentActivity(BaseModel):
    id: str
    kind: str = "application"
    title: str
    detail: str | None = None
    at: str | None = None


class EmployerDashboard(BaseModel):
    open_roles: int = 0
    pipeline: list[PipelineStage] = Field(default_factory=list)
    time_to_fill: float | None = None
    flight_risk_count: int = 0
    applications_total: int = 0
    offers_out: int = 0
    recent_activity: list[RecentActivity] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Onboarding Success Predictor
# --------------------------------------------------------------------------- #


class OnboardingRisk(BaseModel):
    id: str
    full_name: str
    headline: str | None = None
    role: str | None = None
    risk_level: str | None = None  # low | medium | high
    risk_score: float = Field(ge=0.0, le=1.0)
    glass_box: GlassBox


class OnboardingReport(BaseModel):
    items: list[OnboardingRisk] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Warm-bench re-engagement
# --------------------------------------------------------------------------- #


class ReengagementCandidate(BaseModel):
    id: str
    full_name: str
    headline: str | None = None
    former_role: str | None = None
    reason: str | None = None
    fit_score: float | None = None
    suggested_job_id: str | None = None
    glass_box: GlassBox


class ReengagementReport(BaseModel):
    items: list[ReengagementCandidate] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Workforce Resilience
# --------------------------------------------------------------------------- #


class WorkforceProjection(BaseModel):
    year: int
    working_age: float
    supply_index: float


class WorkforceScenario(BaseModel):
    id: str
    title: str
    description: str | None = None
    impact: str | None = None
    horizon_years: int | None = None
    delta_pct: float | None = None


class WorkforceReport(BaseModel):
    country: str
    projections: list[WorkforceProjection] = Field(default_factory=list)
    scenarios: list[WorkforceScenario] = Field(default_factory=list)
    glass_box: GlassBox


class LLMWorkforceScenario(BaseModel):
    """One scenario as the LLM narrates it (title + description)."""

    title: str
    description: str | None = None


class WorkforceScenarios(BaseModel):
    """LLM-structured payload: the scenario narratives + their Glass Box."""

    scenarios: list[LLMWorkforceScenario] = Field(default_factory=list)
    glass_box: GlassBox
