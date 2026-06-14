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


class PipelineBreakdown(BaseModel):
    """Applicant counts grouped by pipeline stage."""

    by_stage: dict[str, int] = Field(default_factory=dict)


class RecentActivity(BaseModel):
    kind: str
    summary: str
    at: str | None = None
    ref_id: str | None = None


class EmployerDashboard(BaseModel):
    open_roles: int = 0
    total_applicants: int = 0
    pipeline: PipelineBreakdown = Field(default_factory=PipelineBreakdown)
    time_to_fill_days: float | None = None
    flight_risk_count: int = 0
    recent_activity: list[RecentActivity] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Onboarding Success Predictor
# --------------------------------------------------------------------------- #


class OnboardingRisk(BaseModel):
    candidate_id: str
    application_id: str
    candidate_summary: str
    role_title: str | None = None
    risk_score: float = Field(ge=0.0, le=1.0)
    glass_box: GlassBox


class OnboardingReport(BaseModel):
    items: list[OnboardingRisk] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Warm-bench re-engagement
# --------------------------------------------------------------------------- #


class ReengagementCandidate(BaseModel):
    candidate_id: str
    application_id: str
    candidate_summary: str
    previous_status: str
    suggested_role: str
    suggested_job_id: str | None = None
    glass_box: GlassBox


class ReengagementReport(BaseModel):
    items: list[ReengagementCandidate] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Workforce Resilience
# --------------------------------------------------------------------------- #


class WorkforceProjection(BaseModel):
    year: int
    working_age_index: float
    supply_index: float


class WorkforceScenario(BaseModel):
    name: str
    summary: str


class WorkforceReport(BaseModel):
    country: str
    projections: list[WorkforceProjection] = Field(default_factory=list)
    scenarios: list[WorkforceScenario] = Field(default_factory=list)
    glass_box: GlassBox


class WorkforceScenarios(BaseModel):
    """LLM-structured payload: the scenario narratives + their Glass Box."""

    scenarios: list[WorkforceScenario] = Field(default_factory=list)
    glass_box: GlassBox
