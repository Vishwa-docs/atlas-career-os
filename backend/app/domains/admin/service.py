"""Admin Mission Control business logic: KPIs, tenants, users, taxonomy, usage, audit."""

from __future__ import annotations

import uuid

from app.core.schemas import Page, PageParams
from app.domains.admin.models import AuditLog
from app.domains.admin.repository import AdminRepository
from app.domains.admin.schemas import (
    AdminUserRead,
    AiUsageReport,
    AuditLogRead,
    Breakdown,
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
        by_role = await self.repo.signups_by_role()
        by_type = await self.repo.orgs_by_type()
        return PlatformMetrics(
            total_users=await self.repo.count_users(),
            total_orgs=await self.repo.count_total_orgs(),
            total_jobs=await self.repo.count_jobs(),
            total_applications=await self.repo.count_applications(),
            ai_calls_30d=await self.repo.count_ai_calls(),
            ai_cost_usd_30d=round(await self.repo.total_llm_cost(), 6),
            candidates=await self.repo.count_candidates(),
            employers=await self.repo.count_orgs_by_type("employer"),
            universities=await self.repo.count_orgs_by_type("university"),
            signups_by_role=[Breakdown(label=r, value=n) for r, n in by_role],
            orgs_by_type=[Breakdown(label=t, value=n) for t, n in by_type],
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
        org_names = await self.repo.org_names_for_users([u.id for u in rows])
        return Page[AdminUserRead](
            items=[self._user(u, org_names.get(u.id)) for u in rows],
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
        total_cost, tokens, prompt, completion, calls = await self.repo.usage_totals()
        by_feature = await self.repo.usage_by_feature()
        by_day = await self.repo.usage_by_day()
        return AiUsageReport(
            total_cost_usd=round(total_cost, 6),
            tokens=tokens,
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_calls=calls,
            by_feature=[
                UsageByFeature(feature=f, cost_usd=round(c, 6), calls=n) for f, c, n in by_feature
            ],
            by_day=[UsageByDay(date=d, cost_usd=round(c, 6)) for d, c in by_day],
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
        actor_ids = [a.actor_id for a in rows if a.actor_id]
        identities = await self.repo.actor_identities(actor_ids)
        return Page[AuditLogRead](
            items=[self._audit(a, identities) for a in rows],
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
    def _user(u: User, org_name: str | None = None) -> AdminUserRead:
        return AdminUserRead(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            roles=list(u.roles or []),
            org_name=org_name,
            status="active" if u.is_active else "inactive",
            last_active_at=u.last_login_at,
            created_at=u.created_at,
        )

    @staticmethod
    def _audit(
        a: AuditLog, identities: dict[uuid.UUID, tuple[str, str]] | None = None
    ) -> AuditLogRead:
        identities = identities or {}
        name = email = None
        if a.actor_id and a.actor_id in identities:
            name, email = identities[a.actor_id]
        return AuditLogRead(
            id=str(a.id),
            action=a.action,
            actor_id=str(a.actor_id) if a.actor_id else None,
            actor_name=name,
            actor_email=email,
            org_id=str(a.org_id) if a.org_id else None,
            resource_type=a.resource_type,
            resource_id=a.resource_id,
            ip=a.ip,
            detail=a.detail or {},
            at=a.created_at,
        )
