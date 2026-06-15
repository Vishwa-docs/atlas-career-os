"""All DB queries for employer analytics — strictly scoped to one org.

Every query takes ``org_id`` and filters jobs (and applications via their job)
to that organization, so the service layer cannot leak cross-tenant data.
Robust to sparse data: aggregates return empty/zero rather than raising.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.applications.models import Application
from app.domains.candidates.models import CandidateProfile
from app.domains.jobs.models import Job
from app.domains.signals.models import Signal
from app.domains.users.models import User


class EmployerRepository:
    """Read-only analytics queries for a single employer org."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_open_roles(self, org_id: uuid.UUID) -> int:
        stmt = (
            select(func.count()).select_from(Job).where(Job.org_id == org_id, Job.status == "open")
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def org_job_ids(self, org_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(Job.id).where(Job.org_id == org_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def pipeline_by_stage(self, org_id: uuid.UUID) -> dict[str, int]:
        """Count applications to this org's jobs, grouped by status."""
        stmt = (
            select(Application.status, func.count())
            .join(Job, Job.id == Application.job_id)
            .where(Job.org_id == org_id)
            .group_by(Application.status)
        )
        rows = (await self.session.execute(stmt)).all()
        return {status: int(count) for status, count in rows}

    async def total_applicants(self, org_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Application)
            .join(Job, Job.id == Application.job_id)
            .where(Job.org_id == org_id)
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def avg_time_to_fill_days(self, org_id: uuid.UUID) -> float | None:
        """Mean days between a hired application's creation and last update."""
        delta = func.extract("epoch", Application.updated_at - Application.created_at) / 86400.0
        stmt = (
            select(func.avg(delta))
            .join(Job, Job.id == Application.job_id)
            .where(Job.org_id == org_id, Application.status == "hired")
        )
        val = (await self.session.execute(stmt)).scalar_one_or_none()
        return round(float(val), 1) if val is not None else None

    async def flight_risk_count(self, org_id: uuid.UUID) -> int:
        """Open retention-type signals observed within this org."""
        risky = ("activity_drop", "peer_departure", "underpaid", "plateau")
        stmt = (
            select(func.count())
            .select_from(Signal)
            .where(
                Signal.org_id == org_id,
                Signal.status == "open",
                Signal.type.in_(risky),
            )
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def recent_applications(
        self, org_id: uuid.UUID, limit: int = 10
    ) -> list[tuple[Application, Job]]:
        stmt = (
            select(Application, Job)
            .join(Job, Job.id == Application.job_id)
            .where(Job.org_id == org_id)
            .order_by(Application.updated_at.desc())
            .limit(limit)
        )
        return [(a, j) for a, j in (await self.session.execute(stmt)).all()]

    async def applications_by_status(
        self,
        org_id: uuid.UUID,
        statuses: tuple[str, ...],
        limit: int = 25,
    ) -> list[tuple[Application, Job, CandidateProfile, str | None]]:
        """Applications in given statuses joined to job, candidate, and full name."""
        stmt = (
            select(Application, Job, CandidateProfile, User.full_name)
            .join(Job, Job.id == Application.job_id)
            .join(CandidateProfile, CandidateProfile.id == Application.candidate_id)
            .join(User, User.id == CandidateProfile.user_id, isouter=True)
            .where(Job.org_id == org_id, Application.status.in_(statuses))
            .order_by(Application.updated_at.desc())
            .limit(limit)
        )
        return [(a, j, c, n) for a, j, c, n in (await self.session.execute(stmt)).all()]

    async def open_roles(self, org_id: uuid.UUID, limit: int = 10) -> list[Job]:
        stmt = (
            select(Job)
            .where(Job.org_id == org_id, Job.status == "open")
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def open_signals_for_candidate(
        self, org_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> list[Signal]:
        stmt = select(Signal).where(
            Signal.org_id == org_id,
            Signal.subject_candidate_id == candidate_id,
            Signal.status == "open",
        )
        return list((await self.session.execute(stmt)).scalars().all())
