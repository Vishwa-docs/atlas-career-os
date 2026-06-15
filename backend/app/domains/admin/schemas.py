"""Admin / Mission Control read schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel


class Breakdown(BaseModel):
    label: str
    value: int


class PlatformMetrics(BaseModel):
    total_users: int
    total_orgs: int
    total_jobs: int = 0
    total_applications: int = 0
    ai_calls_30d: int = 0
    ai_cost_usd_30d: float = 0.0
    # Extra context tiles / charts on the Overview page.
    candidates: int = 0
    employers: int = 0
    universities: int = 0
    signups_by_role: list[Breakdown] = Field(default_factory=list)
    orgs_by_type: list[Breakdown] = Field(default_factory=list)


class TenantRead(ORMModel):
    id: str
    name: str
    type: str
    tier: str | None = None
    country: str = "MY"
    industry: str | None = None
    created_at: datetime | None = None


class AdminUserRead(ORMModel):
    id: str
    email: str
    full_name: str
    roles: list[str]
    org_name: str | None = None
    status: str | None = None  # active | inactive
    last_active_at: datetime | None = None
    created_at: datetime | None = None


class TaxonomyCounts(BaseModel):
    skills: int
    occupations: int
    transitions: int


class UsageByFeature(BaseModel):
    feature: str
    cost_usd: float
    calls: int = 0


class UsageByDay(BaseModel):
    date: str
    cost_usd: float


class AiUsageReport(BaseModel):
    total_cost_usd: float
    tokens: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_calls: int = 0
    by_feature: list[UsageByFeature]
    by_day: list[UsageByDay]


class AuditLogRead(ORMModel):
    id: str
    action: str
    actor_id: str | None = None
    actor_name: str | None = None
    actor_email: str | None = None
    org_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    ip: str | None = None
    status: str | None = None
    detail: dict = Field(default_factory=dict)
    at: datetime | None = None
