"""Admin Mission Control business logic: KPIs, tenants, users, taxonomy, usage, audit."""

from __future__ import annotations

from app.core.schemas import Page, PageParams
from app.domains.admin.models import AuditLog
from app.domains.admin.repository import AdminRepository
from app.domains.admin.schemas import (
    AdminUserRead,
    AiUsageReport,
    AuditLogRead,
    PlatformMetrics,
    TaxonomyCounts,
    TenantRead,
    UsageByDay,
    UsageByFeature,
)
from app.domains.organizations.models import Organization
from app.domains.users.models import User


class AdminService:
    def __init__(self, repo: AdminRepository) -> None:
        self.repo = repo
        self.session = repo.session

    async def metrics(self) -> PlatformMetrics:
        return PlatformMetrics(
            users=await self.repo.count_users(),
            candidates=await self.repo.count_candidates(),
            employers=await self.repo.count_orgs_by_type("employer"),
            universities=await self.repo.count_orgs_by_type("university"),
            jobs=await self.repo.count_jobs(),
            applications=await self.repo.count_applications(),
            llm_cost_usd=round(await self.repo.total_llm_cost(), 6),
        )

    async def tenants(self, params: PageParams) -> Page[TenantRead]:
        orgs, total = await self.repo.list_orgs(params.offset, params.limit)
        return Page[TenantRead](
            items=[self._tenant(o) for o in orgs],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def users(self, params: PageParams) -> Page[AdminUserRead]:
        rows, total = await self.repo.list_users(params.offset, params.limit)
        return Page[AdminUserRead](
            items=[self._user(u) for u in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def taxonomy(self) -> TaxonomyCounts:
        return TaxonomyCounts(
            skills=await self.repo.count_skills(),
            occupations=await self.repo.count_occupations(),
            transitions=await self.repo.count_transitions(),
        )

    async def ai_usage(self) -> AiUsageReport:
        total_cost, tokens = await self.repo.usage_totals()
        by_feature = await self.repo.usage_by_feature()
        by_day = await self.repo.usage_by_day()
        return AiUsageReport(
            total_cost_usd=round(total_cost, 6),
            tokens=tokens,
            by_feature=[
                UsageByFeature(feature=f, cost=round(c, 6), calls=n) for f, c, n in by_feature
            ],
            by_day=[UsageByDay(day=d, cost=round(c, 6)) for d, c in by_day],
        )

    async def audit(
        self,
        params: PageParams,
        *,
        action: str | None = None,
        actor: str | None = None,
    ) -> Page[AuditLogRead]:
        rows, total = await self.repo.list_audit(
            params.offset, params.limit, action=action, actor=actor
        )
        return Page[AuditLogRead](
            items=[self._audit(a) for a in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    # --- Mappers (ORM -> schema with str ids) ---
    @staticmethod
    def _tenant(o: Organization) -> TenantRead:
        return TenantRead(
            id=str(o.id),
            name=o.name,
            type=o.type,
            tier=o.tier,
            country=o.country,
            industry=o.industry,
            created_at=o.created_at,
        )

    @staticmethod
    def _user(u: User) -> AdminUserRead:
        return AdminUserRead(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            roles=list(u.roles or []),
            is_active=u.is_active,
            is_verified=u.is_verified,
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )

    @staticmethod
    def _audit(a: AuditLog) -> AuditLogRead:
        return AuditLogRead(
            id=str(a.id),
            actor_id=str(a.actor_id) if a.actor_id else None,
            org_id=str(a.org_id) if a.org_id else None,
            action=a.action,
            resource_type=a.resource_type,
            resource_id=a.resource_id,
            ip=a.ip,
            detail=a.detail or {},
            created_at=a.created_at,
        )
