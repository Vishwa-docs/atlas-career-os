"""Admin / Mission Control read schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.core.schemas import ORMModel


class PlatformMetrics(BaseModel):
    users: int
    candidates: int
    employers: int
    universities: int
    jobs: int
    applications: int
    llm_cost_usd: float


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
    is_active: bool = True
    is_verified: bool = False
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class TaxonomyCounts(BaseModel):
    skills: int
    occupations: int
    transitions: int


class UsageByFeature(BaseModel):
    feature: str
    cost: float
    calls: int


class UsageByDay(BaseModel):
    day: str
    cost: float


class AiUsageReport(BaseModel):
    total_cost_usd: float
    tokens: int
    by_feature: list[UsageByFeature]
    by_day: list[UsageByDay]


class AuditLogRead(ORMModel):
    id: str
    actor_id: str | None = None
    org_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    ip: str | None = None
    detail: dict
    created_at: datetime | None = None
