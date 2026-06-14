"""All database access for the candidates domain.

Async SQLAlchemy 2.0 ``select()`` style. The service layer owns business logic
and transaction boundaries; this layer only reads/writes rows.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.candidates.models import CandidateProfile, CandidateSkill, CareerEvent
from app.domains.consent.models import ConsentGrant
from app.domains.taxonomy.models import Skill


def _slugify(name: str) -> str:
    """Lowercase, hyphenated slug used to resolve/create taxonomy skills."""
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in name.lower())
    return "-".join(cleaned.split())[:160] or "skill"


class CandidateRepository:
    """Encapsulates queries for profiles, career events, skills, and consent."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------- profile -------------------------------- #
    async def get_profile_by_user(self, user_id: uuid.UUID) -> CandidateProfile | None:
        stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_profile_by_id(self, profile_id: uuid.UUID) -> CandidateProfile | None:
        stmt = select(CandidateProfile).where(CandidateProfile.id == profile_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def add_profile(self, profile: CandidateProfile) -> CandidateProfile:
        self.session.add(profile)
        return profile

    # --------------------------- career events ---------------------------- #
    async def list_career_events(self, candidate_id: uuid.UUID) -> list[CareerEvent]:
        stmt = (
            select(CareerEvent)
            .where(CareerEvent.candidate_id == candidate_id)
            .order_by(CareerEvent.start_date.desc().nullslast(), CareerEvent.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_career_event(self, event_id: uuid.UUID) -> CareerEvent | None:
        stmt = select(CareerEvent).where(CareerEvent.id == event_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def add_career_event(self, event: CareerEvent) -> CareerEvent:
        self.session.add(event)
        return event

    async def delete_career_event(self, event: CareerEvent) -> None:
        await self.session.delete(event)

    # ------------------------------ skills -------------------------------- #
    async def list_candidate_skills(
        self, candidate_id: uuid.UUID
    ) -> list[tuple[CandidateSkill, Skill]]:
        """Return (candidate_skill, skill) pairs joined to the taxonomy."""
        stmt = (
            select(CandidateSkill, Skill)
            .join(Skill, Skill.id == CandidateSkill.skill_id)
            .where(CandidateSkill.candidate_id == candidate_id)
            .order_by(CandidateSkill.proficiency.desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows]

    async def get_skill_by_name(self, name: str) -> Skill | None:
        slug = _slugify(name)
        stmt = select(Skill).where(
            or_(func.lower(Skill.name) == name.strip().lower(), Skill.slug == slug)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def resolve_or_create_skill(self, name: str) -> Skill:
        """Find a taxonomy skill by name/slug, creating a minimal one if absent."""
        existing = await self.get_skill_by_name(name)
        if existing is not None:
            return existing
        skill = Skill(name=name.strip()[:160], slug=_slugify(name))
        self.session.add(skill)
        await self.session.flush()
        return skill

    async def get_candidate_skill(
        self, candidate_id: uuid.UUID, skill_id: uuid.UUID
    ) -> CandidateSkill | None:
        stmt = select(CandidateSkill).where(
            and_(
                CandidateSkill.candidate_id == candidate_id,
                CandidateSkill.skill_id == skill_id,
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def add_candidate_skill(self, cskill: CandidateSkill) -> CandidateSkill:
        self.session.add(cskill)
        return cskill

    async def clear_candidate_skills(self, candidate_id: uuid.UUID) -> None:
        for cskill, _ in await self.list_candidate_skills(candidate_id):
            await self.session.delete(cskill)

    # ------------------------------ counts -------------------------------- #
    async def count_career_events(self, candidate_id: uuid.UUID) -> int:
        stmt = select(func.count(CareerEvent.id)).where(CareerEvent.candidate_id == candidate_id)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def count_skills(self, candidate_id: uuid.UUID) -> int:
        stmt = select(func.count(CandidateSkill.id)).where(
            CandidateSkill.candidate_id == candidate_id
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    # ------------------------------ consent ------------------------------- #
    async def active_grant(
        self, candidate_id: uuid.UUID, grantee_org_id: uuid.UUID, scope: str
    ) -> ConsentGrant | None:
        """An active (not revoked, not expired) grant covering ``scope``, if any."""
        now = datetime.now(UTC)
        stmt = select(ConsentGrant).where(
            and_(
                ConsentGrant.candidate_id == candidate_id,
                ConsentGrant.grantee_org_id == grantee_org_id,
                ConsentGrant.revoked_at.is_(None),
                or_(ConsentGrant.expires_at.is_(None), ConsentGrant.expires_at > now),
                ConsentGrant.scopes.any(scope),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_active_scopes(
        self, candidate_id: uuid.UUID, grantee_org_id: uuid.UUID
    ) -> set[str]:
        """All scopes the org currently has active grants for on this candidate."""
        now = datetime.now(UTC)
        stmt = select(ConsentGrant.scopes).where(
            and_(
                ConsentGrant.candidate_id == candidate_id,
                ConsentGrant.grantee_org_id == grantee_org_id,
                ConsentGrant.revoked_at.is_(None),
                or_(ConsentGrant.expires_at.is_(None), ConsentGrant.expires_at > now),
            )
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        scopes: set[str] = set()
        for arr in rows:
            scopes.update(arr or [])
        return scopes
