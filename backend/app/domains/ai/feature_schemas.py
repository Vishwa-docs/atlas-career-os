"""Structured response schemas for Atlas's signature AI features.

Every model here ends in ``glass_box: GlassBox`` — the trust contract. These are
the exact shapes the API contract promises, and the schemas the LLM is asked to
fill via constrained decoding (the mock builds valid instances too).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.domains.ai.schemas import GlassBox


# --------------------------------------------------------------------------- #
# Shared value objects
# --------------------------------------------------------------------------- #
class SalaryRange(BaseModel):
    min: int = 0
    max: int = 0
    median: int = 0
    currency: str = "MYR"


class TimeMonths(BaseModel):
    min: int = 0
    max: int = 0


class SkillGap(BaseModel):
    skill: str
    have: float = Field(ge=0.0, le=1.0, default=0.0)
    need: float = Field(ge=0.0, le=1.0, default=0.0)


class CurrentRole(BaseModel):
    occupation: str
    occupation_id: str | None = None


class MarketBand(BaseModel):
    p25: int = 0
    p50: int = 0
    p75: int = 0
    currency: str = "MYR"


class Negotiation(BaseModel):
    timing: str
    script: str
    talking_points: list[str] = Field(default_factory=list)


class RampStep(BaseModel):
    step: str
    resource: str
    months: int = 0


class Outlook(StrEnum):
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    STORMY = "stormy"


# --------------------------------------------------------------------------- #
# Coach
# --------------------------------------------------------------------------- #
class CoachReply(BaseModel):
    """A single co-pilot turn with its reasoning envelope."""

    message: str
    glass_box: GlassBox


# --------------------------------------------------------------------------- #
# Trajectory Atlas
# --------------------------------------------------------------------------- #
class AtlasRoute(BaseModel):
    """One realistic route on the candidate's trajectory map."""

    id: str
    title: str
    occupation_id: str | None = None
    salary_range: SalaryRange = Field(default_factory=SalaryRange)
    time_months: TimeMonths = Field(default_factory=TimeMonths)
    feasibility: float = Field(ge=0.0, le=1.0, default=0.5)
    demand_trend: float = 0.0
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    trade_offs: list[str] = Field(default_factory=list)
    glass_box: GlassBox


class AtlasResponse(BaseModel):
    current: CurrentRole
    routes: list[AtlasRoute] = Field(default_factory=list)
    glass_box: GlassBox


# --------------------------------------------------------------------------- #
# Fair Pay
# --------------------------------------------------------------------------- #
class FairPayResponse(BaseModel):
    role: str
    location: str
    market: MarketBand = Field(default_factory=MarketBand)
    your_pay: int | None = None
    gap_pct: float | None = None
    verdict: str
    negotiation: Negotiation
    glass_box: GlassBox


# --------------------------------------------------------------------------- #
# Career Weather
# --------------------------------------------------------------------------- #
class WeatherResponse(BaseModel):
    role: str
    region: str
    outlook: Outlook = Outlook.CLOUDY
    summary: str
    demand_index: float = Field(default=0.5)
    rising_skills: list[str] = Field(default_factory=list)
    cooling_skills: list[str] = Field(default_factory=list)
    salary_drift_pct: float = 0.0
    glass_box: GlassBox


# --------------------------------------------------------------------------- #
# Pivot feasibility
# --------------------------------------------------------------------------- #
class PivotResponse(BaseModel):
    feasibility: float = Field(ge=0.0, le=1.0, default=0.5)
    gap: list[SkillGap] = Field(default_factory=list)
    ramp: list[RampStep] = Field(default_factory=list)
    glass_box: GlassBox


# --------------------------------------------------------------------------- #
# Prose-only schemas (internal)
#
# The numeric/factual fields of every feature are computed deterministically in
# Python from the seeded database. The LLM is asked ONLY for the human prose,
# grounded in those already-computed numbers. These small schemas are what we
# hand to ``llm.structured(...)`` — they never leave the service layer and are
# not part of the API contract.
# --------------------------------------------------------------------------- #
class GlassBoxProse(BaseModel):
    """The free-text parts of a GlassBox the model is allowed to author."""

    rationale: str = ""
    what_would_change_this: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class AtlasRouteProse(GlassBoxProse):
    trade_offs: list[str] = Field(default_factory=list)


class FairPayProse(GlassBoxProse):
    timing: str = ""
    script: str = ""
    talking_points: list[str] = Field(default_factory=list)


class WeatherProse(GlassBoxProse):
    summary: str = ""


class PivotStepProse(BaseModel):
    step: str = ""
    resource: str = ""


class PivotProse(GlassBoxProse):
    ramp_steps: list[PivotStepProse] = Field(default_factory=list)


__all__ = [
    "SalaryRange",
    "TimeMonths",
    "SkillGap",
    "CurrentRole",
    "MarketBand",
    "Negotiation",
    "RampStep",
    "Outlook",
    "CoachReply",
    "AtlasRoute",
    "AtlasResponse",
    "FairPayResponse",
    "WeatherResponse",
    "PivotResponse",
    "GlassBoxProse",
    "AtlasRouteProse",
    "FairPayProse",
    "WeatherProse",
    "PivotStepProse",
    "PivotProse",
]
