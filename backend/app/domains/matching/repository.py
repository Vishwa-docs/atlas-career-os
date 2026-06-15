"""All database access for the matching domain (async SQLAlchemy 2.0).

Keeps every query in one place so the service layer stays pure business logic.
Cross-domain reads (jobs, candidates, skills, transitions, consent) are
performed here against the owning models, which we import read-only.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.candidates.models import (
    CandidateProfile,
    CandidateSkill,
)
from app.domains.consent.models import ConsentGrant
from app.domains.jobs.models import Job
from app.domains.matching.models import MatchResult
from app.domains.taxonomy.models import OccupationTransition, Skill
from app.domains.users.models import User


class MatchingRepository:
    """Read/write helpers for explainable matching."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------ #
    # Candidates
    # ------------------------------------------------------------------ #
    async def get_candidate(self, candidate_id: uuid.UUID) -> CandidateProfile | None:
        return await self.session.get(CandidateProfile, candidate_id)

    async def get_candidate_by_user(self, user_id: uuid.UUID) -> CandidateProfile | None:
        stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def candidate_names(
        self, candidate_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        """Map candidate-profile id → user's full name (one batched query)."""
        if not candidate_ids:
            return {}
        stmt = (
            select(CandidateProfile.id, User.full_name)
            .join(User, User.id == CandidateProfile.user_id)
            .where(CandidateProfile.id.in_(candidate_ids))
        )
        rows = (await self.session.execute(stmt)).all()
        return {cid: name for cid, name in rows if name}

    async def candidate_skill_names(self, candidate_id: uuid.UUID) -> list[str]:
        """Return the candidate's skill names (lower-cased) via the join table."""
        stmt = (
            select(Skill.name, CandidateSkill.proficiency)
            .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
            .where(CandidateSkill.candidate_id == candidate_id)
            .order_by(CandidateSkill.proficiency.desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [name for (name, _prof) in rows]

    # ------------------------------------------------------------------ #
    # Jobs
    # ------------------------------------------------------------------ #
    async def get_job(self, job_id: uuid.UUID) -> Job | None:
        return await self.session.get(Job, job_id)

    async def open_jobs(self, limit: int = 200) -> list[Job]:
        """Candidate-facing pool: open postings, newest first."""
        stmt = select(Job).where(Job.status == "open").order_by(Job.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    # ------------------------------------------------------------------ #
    # Trajectory
    # ------------------------------------------------------------------ #
    async def transition_weight(
        self, from_occ: uuid.UUID, to_occ: uuid.UUID
    ) -> OccupationTransition | None:
        stmt = select(OccupationTransition).where(
            OccupationTransition.from_occupation_id == from_occ,
            OccupationTransition.to_occupation_id == to_occ,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    # ------------------------------------------------------------------ #
    # Employer-facing candidate discovery (consent-gated)
    # ------------------------------------------------------------------ #
    async def visible_candidates_for_org(
        self, org_id: uuid.UUID, *, query: str | None, limit: int
    ) -> list[tuple[CandidateProfile, bool]]:
        """Candidates an org may view, each flagged with whether the basis is
        an active :class:`ConsentGrant` (``True``) or just ``open_to_work``.

        Active grant = not revoked and (no expiry or expiry in the future).
        """
        now = datetime.now(UTC)
        active_grant = and_(
            ConsentGrant.candidate_id == CandidateProfile.id,
            ConsentGrant.grantee_org_id == org_id,
            ConsentGrant.revoked_at.is_(None),
            or_(ConsentGrant.expires_at.is_(None), ConsentGrant.expires_at > now),
        )
        granted_exists = select(ConsentGrant.id).where(active_grant).exists()

        stmt = select(CandidateProfile).where(
            or_(granted_exists, CandidateProfile.open_to_work.is_(True))
        )
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    CandidateProfile.headline.ilike(like),
                    CandidateProfile.summary.ilike(like),
                    CandidateProfile.aspirations.ilike(like),
                )
            )
        stmt = stmt.order_by(CandidateProfile.completeness.desc()).limit(limit)
        candidates = list((await self.session.execute(stmt)).scalars().all())

        # Resolve the consent basis per candidate (one batched grant lookup).
        if not candidates:
            return []
        grant_stmt = select(ConsentGrant.candidate_id).where(
            ConsentGrant.grantee_org_id == org_id,
            ConsentGrant.revoked_at.is_(None),
            or_(ConsentGrant.expires_at.is_(None), ConsentGrant.expires_at > now),
            ConsentGrant.candidate_id.in_([c.id for c in candidates]),
        )
        granted_ids = set((await self.session.execute(grant_stmt)).scalars().all())
        return [(c, c.id in granted_ids) for c in candidates]

    # ------------------------------------------------------------------ #
    # MatchResult cache (upsert)
    # ------------------------------------------------------------------ #
    async def get_match(self, candidate_id: uuid.UUID, job_id: uuid.UUID) -> MatchResult | None:
        stmt = select(MatchResult).where(
            MatchResult.candidate_id == candidate_id,
            MatchResult.job_id == job_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upsert_match(
        self,
        *,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
        score: float,
        sub_scores: dict[str, float],
        glass_box: dict,
        model_version: str = "v1",
    ) -> MatchResult:
        """Insert or update the cached, explained match for this pair."""
        existing = await self.get_match(candidate_id, job_id)
        if existing is None:
            existing = MatchResult(candidate_id=candidate_id, job_id=job_id)
            self.session.add(existing)
        existing.score = score
        existing.semantic_score = sub_scores["semantic"]
        existing.skill_overlap = sub_scores["skill_overlap"]
        existing.trajectory_fit = sub_scores["trajectory_fit"]
        existing.salary_fit = sub_scores["salary_fit"]
        existing.glass_box = glass_box
        existing.model_version = model_version
        return existing
