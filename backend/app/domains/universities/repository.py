"""All DB queries for the university Outcomes Studio — scoped to one org.

Cohorts carry ``university_org_id``; outcomes link to cohorts; students link to
cohorts. Every query starts from the org's cohorts so no cross-tenant rows leak.
Aggregates tolerate empty data (return None/0/[] rather than raising).
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.candidates.models import CandidateProfile, CandidateSkill, CareerEvent
from app.domains.credentials.models import Credential
from app.domains.taxonomy.models import Skill
from app.domains.universities.models import (
    Cohort,
    CohortStudent,
    Internship,
    Outcome,
)
from app.domains.users.models import User


class UniversityRepository:
    """Read/write queries for a single university org."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------- cohorts ---------------------------- #
    async def cohort_ids(self, org_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(Cohort.id).where(Cohort.university_org_id == org_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_cohorts(self, org_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Cohort).where(Cohort.university_org_id == org_id)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def cohorts(self, org_id: uuid.UUID) -> list[Cohort]:
        stmt = select(Cohort).where(Cohort.university_org_id == org_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_cohort(self, org_id: uuid.UUID, cohort_id: uuid.UUID) -> Cohort | None:
        stmt = select(Cohort).where(Cohort.id == cohort_id, Cohort.university_org_id == org_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    # ----------------------------- outcomes --------------------------- #
    async def outcomes(
        self,
        org_id: uuid.UUID,
        cohort_id: uuid.UUID | None = None,
        year: int | None = None,
    ) -> list[tuple[Outcome, Cohort]]:
        """Outcomes for this org's cohorts, optionally filtered."""
        stmt = (
            select(Outcome, Cohort)
            .join(Cohort, Cohort.id == Outcome.cohort_id)
            .where(Cohort.university_org_id == org_id)
        )
        if cohort_id is not None:
            stmt = stmt.where(Cohort.id == cohort_id)
        if year is not None:
            stmt = stmt.where(Cohort.graduation_year == year)
        return [(o, c) for o, c in (await self.session.execute(stmt)).all()]

    async def tracked_graduates(self, org_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(func.distinct(Outcome.candidate_id)))
            .join(Cohort, Cohort.id == Outcome.cohort_id)
            .where(Cohort.university_org_id == org_id)
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def active_students(self, org_id: uuid.UUID) -> int:
        """Distinct students enrolled across the org's cohorts."""
        stmt = (
            select(func.count(func.distinct(CohortStudent.candidate_id)))
            .join(Cohort, Cohort.id == CohortStudent.cohort_id)
            .where(Cohort.university_org_id == org_id)
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def program_count(self, org_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(func.distinct(Cohort.program)))
            .where(Cohort.university_org_id == org_id)
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def open_internship_count(self, org_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Internship)
            .where(Internship.org_id == org_id, Internship.status == "open")
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def credentials_issued(self, org_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Credential)
            .where(Credential.issuer_org_id == org_id)
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    # ----------------------------- students --------------------------- #
    async def roster(
        self, org_id: uuid.UUID, limit: int = 200
    ) -> list[tuple[CohortStudent, Cohort, CandidateProfile, str | None]]:
        stmt = (
            select(CohortStudent, Cohort, CandidateProfile, User.full_name)
            .join(Cohort, Cohort.id == CohortStudent.cohort_id)
            .join(
                CandidateProfile,
                CandidateProfile.id == CohortStudent.candidate_id,
            )
            .join(User, User.id == CandidateProfile.user_id, isouter=True)
            .where(Cohort.university_org_id == org_id)
            .limit(limit)
        )
        return [(s, c, p, n) for s, c, p, n in (await self.session.execute(stmt)).all()]

    async def student_in_org(
        self, org_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> tuple[CohortStudent, Cohort, CandidateProfile, str | None] | None:
        """Resolve a single roster row, enforcing org membership (BOLA)."""
        stmt = (
            select(CohortStudent, Cohort, CandidateProfile, User.full_name)
            .join(Cohort, Cohort.id == CohortStudent.cohort_id)
            .join(
                CandidateProfile,
                CandidateProfile.id == CohortStudent.candidate_id,
            )
            .join(User, User.id == CandidateProfile.user_id, isouter=True)
            .where(
                Cohort.university_org_id == org_id,
                CohortStudent.candidate_id == candidate_id,
            )
            .limit(1)
        )
        row = (await self.session.execute(stmt)).first()
        return (row[0], row[1], row[2], row[3]) if row else None

    # --------------------- candidate enrichment ----------------------- #
    async def candidate_skills(self, candidate_id: uuid.UUID) -> list[tuple[CandidateSkill, Skill]]:
        stmt = (
            select(CandidateSkill, Skill)
            .join(Skill, Skill.id == CandidateSkill.skill_id)
            .where(CandidateSkill.candidate_id == candidate_id)
        )
        return [(cs, s) for cs, s in (await self.session.execute(stmt)).all()]

    async def candidate_events(self, candidate_id: uuid.UUID) -> list[CareerEvent]:
        stmt = select(CareerEvent).where(CareerEvent.candidate_id == candidate_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def cohort_skill_names(self, org_id: uuid.UUID) -> set[str]:
        """Distinct skill names held by students across the org's cohorts."""
        stmt = (
            select(func.distinct(Skill.name))
            .select_from(CohortStudent)
            .join(Cohort, Cohort.id == CohortStudent.cohort_id)
            .join(
                CandidateSkill,
                CandidateSkill.candidate_id == CohortStudent.candidate_id,
            )
            .join(Skill, Skill.id == CandidateSkill.skill_id)
            .where(Cohort.university_org_id == org_id)
        )
        return {n for (n,) in (await self.session.execute(stmt)).all() if n}

    async def top_demand_skills(self, limit: int = 15) -> list[Skill]:
        """Skills with the strongest rising demand (Skill.demand_trend)."""
        stmt = (
            select(Skill)
            .where(Skill.demand_trend > 0)
            .order_by(Skill.demand_trend.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    # ---------------------------- internships ------------------------- #
    async def list_internships(self, org_id: uuid.UUID) -> list[Internship]:
        stmt = (
            select(Internship)
            .where(Internship.org_id == org_id)
            .order_by(Internship.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def add_internship(self, internship: Internship) -> Internship:
        self.session.add(internship)
        await self.session.flush()
        return internship
