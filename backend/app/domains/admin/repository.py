"""DB access for Admin Mission Control: counts, listings, AI-usage rollups, audit.

Cross-domain model imports are wrapped defensively so the admin domain still
boots if a peer domain is not yet present (phased build).
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.admin.models import AuditLog
from app.domains.ai.models import LlmUsage
from app.domains.organizations.models import Membership, Organization
from app.domains.users.models import User

# --- Optional cross-domain models (degrade gracefully if absent) ---
try:  # pragma: no cover - import availability depends on phased build
    from app.domains.candidates.models import CandidateProfile
except ImportError:  # pragma: no cover
    CandidateProfile = None  # type: ignore[assignment]

try:  # pragma: no cover
    from app.domains.jobs.models import Job
except ImportError:  # pragma: no cover
    Job = None  # type: ignore[assignment]

try:  # pragma: no cover
    from app.domains.applications.models import Application
except ImportError:  # pragma: no cover
    Application = None  # type: ignore[assignment]

try:  # pragma: no cover
    from app.domains.taxonomy.models import (
        Occupation,
        OccupationTransition,
        Skill,
    )
except ImportError:  # pragma: no cover
    Occupation = OccupationTransition = Skill = None  # type: ignore[assignment]


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _count(self, model: type | None) -> int:
        if model is None:
            return 0
        result = await self.session.execute(select(func.count()).select_from(model))
        return int(result.scalar_one() or 0)

    # --- Metrics ---
    async def count_users(self) -> int:
        return await self._count(User)

    async def count_candidates(self) -> int:
        return await self._count(CandidateProfile)

    async def count_orgs_by_type(self, org_type: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Organization).where(Organization.type == org_type)
        )
        return int(result.scalar_one() or 0)

    async def count_jobs(self) -> int:
        return await self._count(Job)

    async def count_applications(self) -> int:
        return await self._count(Application)

    async def total_llm_cost(self) -> float:
        result = await self.session.execute(select(func.coalesce(func.sum(LlmUsage.cost_usd), 0.0)))
        return float(result.scalar_one() or 0.0)

    async def count_total_orgs(self) -> int:
        return await self._count(Organization)

    async def count_ai_calls(self) -> int:
        return await self._count(LlmUsage)

    async def signups_by_role(self) -> list[tuple[str, int]]:
        """Count users by their (first) role — drives the Overview breakdown."""
        role = func.coalesce(User.roles[1], "unknown")  # Postgres arrays are 1-indexed.
        result = await self.session.execute(
            select(role, func.count()).group_by(role).order_by(func.count().desc())
        )
        return [(str(r), int(n or 0)) for r, n in result.all()]

    async def orgs_by_type(self) -> list[tuple[str, int]]:
        result = await self.session.execute(
            select(Organization.type, func.count())
            .group_by(Organization.type)
            .order_by(func.count().desc())
        )
        return [(str(t), int(n or 0)) for t, n in result.all()]

    # --- Taxonomy counts ---
    async def count_skills(self) -> int:
        return await self._count(Skill)

    async def count_occupations(self) -> int:
        return await self._count(Occupation)

    async def count_transitions(self) -> int:
        return await self._count(OccupationTransition)

    # --- Tenants ---
    async def list_orgs(self, offset: int, limit: int) -> tuple[list[Organization], int]:
        total_res = await self.session.execute(select(func.count()).select_from(Organization))
        total = int(total_res.scalar_one() or 0)
        rows = await self.session.execute(
            select(Organization)
            .order_by(Organization.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(rows.scalars().all()), total

    # --- Users ---
    async def list_users(self, offset: int, limit: int) -> tuple[list[User], int]:
        total_res = await self.session.execute(select(func.count()).select_from(User))
        total = int(total_res.scalar_one() or 0)
        rows = await self.session.execute(
            select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        )
        return list(rows.scalars().all()), total

    async def org_names_for_users(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        """Map user id → their (first) organization name, if any."""
        if not user_ids:
            return {}
        rows = await self.session.execute(
            select(Membership.user_id, Organization.name)
            .join(Organization, Organization.id == Membership.org_id)
            .where(Membership.user_id.in_(user_ids))
        )
        out: dict[uuid.UUID, str] = {}
        for uid, name in rows.all():
            out.setdefault(uid, name)
        return out

    async def actor_identities(
        self, actor_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[str, str]]:
        """Map actor id → (full_name, email) for audit-log enrichment."""
        if not actor_ids:
            return {}
        rows = await self.session.execute(
            select(User.id, User.full_name, User.email).where(User.id.in_(actor_ids))
        )
        return {uid: (name, email) for uid, name, email in rows.all()}

    # --- AI usage rollups ---
    async def usage_totals(self) -> tuple[float, int, int, int, int]:
        """Return (cost, total_tokens, prompt_tokens, completion_tokens, calls)."""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(LlmUsage.cost_usd), 0.0),
                func.coalesce(func.sum(LlmUsage.prompt_tokens + LlmUsage.completion_tokens), 0),
                func.coalesce(func.sum(LlmUsage.prompt_tokens), 0),
                func.coalesce(func.sum(LlmUsage.completion_tokens), 0),
                func.count(),
            )
        )
        cost, tokens, prompt, completion, calls = result.one()
        return (
            float(cost or 0.0),
            int(tokens or 0),
            int(prompt or 0),
            int(completion or 0),
            int(calls or 0),
        )

    async def usage_by_feature(self) -> list[tuple[str, float, int]]:
        result = await self.session.execute(
            select(
                LlmUsage.feature,
                func.coalesce(func.sum(LlmUsage.cost_usd), 0.0),
                func.count(),
            )
            .group_by(LlmUsage.feature)
            .order_by(func.sum(LlmUsage.cost_usd).desc())
        )
        return [(str(f), float(c or 0.0), int(n or 0)) for f, c, n in result.all()]

    async def usage_by_day(self) -> list[tuple[str, float]]:
        day_col = func.date(LlmUsage.created_at)
        result = await self.session.execute(
            select(day_col, func.coalesce(func.sum(LlmUsage.cost_usd), 0.0))
            .group_by(day_col)
            .order_by(day_col)
        )
        return [(str(d), float(c or 0.0)) for d, c in result.all()]

    # --- Audit ---
    async def list_audit(
        self,
        offset: int,
        limit: int,
        *,
        action: str | None = None,
        actor: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        conditions = []
        if action:
            conditions.append(AuditLog.action == action)
        if actor:
            try:
                conditions.append(AuditLog.actor_id == uuid.UUID(actor))
            except (ValueError, AttributeError):
                conditions.append(AuditLog.actor_id == None)  # noqa: E711

        base = select(AuditLog)
        count_q = select(func.count()).select_from(AuditLog)
        for cond in conditions:
            base = base.where(cond)
            count_q = count_q.where(cond)

        total_res = await self.session.execute(count_q)
        total = int(total_res.scalar_one() or 0)
        rows = await self.session.execute(
            base.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        )
        return list(rows.scalars().all()), total
