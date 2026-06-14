"""All DB queries for consent grants + data export/erasure (async SQLAlchemy 2.0)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.admin.models import AuditLog
from app.domains.candidates.models import (
    CandidateProfile,
    CandidateSkill,
    CareerEvent,
)
from app.domains.consent.models import ConsentGrant
from app.domains.credentials.models import Credential
from app.domains.users.models import User


async def candidate_for_user(
    session: AsyncSession, *, user_id: uuid.UUID
) -> CandidateProfile | None:
    """Resolve the candidate profile owned by a user."""
    return await session.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))


async def get_user(session: AsyncSession, *, user_id: uuid.UUID) -> User | None:
    """Fetch a user by id."""
    return await session.scalar(select(User).where(User.id == user_id))


async def add_grant(session: AsyncSession, grant: ConsentGrant) -> ConsentGrant:
    """Persist a new consent grant (flushed for its id)."""
    session.add(grant)
    await session.flush()
    return grant


async def list_grants(session: AsyncSession, *, candidate_id: uuid.UUID) -> list[ConsentGrant]:
    """All grants (active + past) for a candidate, newest first."""
    rows = await session.scalars(
        select(ConsentGrant)
        .where(ConsentGrant.candidate_id == candidate_id)
        .order_by(ConsentGrant.created_at.desc())
    )
    return list(rows)


async def get_grant_for_candidate(
    session: AsyncSession, *, grant_id: uuid.UUID, candidate_id: uuid.UUID
) -> ConsentGrant | None:
    """Fetch one grant scoped to its owning candidate (BOLA defence)."""
    return await session.scalar(
        select(ConsentGrant).where(
            ConsentGrant.id == grant_id,
            ConsentGrant.candidate_id == candidate_id,
        )
    )


async def access_log_for_candidate(
    session: AsyncSession, *, candidate_id: uuid.UUID
) -> list[AuditLog]:
    """Audit rows recording access to this candidate's record."""
    rows = await session.scalars(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "candidate",
            AuditLog.resource_id == str(candidate_id),
        )
        .order_by(AuditLog.created_at.desc())
    )
    return list(rows)


async def career_events(session: AsyncSession, *, candidate_id: uuid.UUID) -> list[CareerEvent]:
    """A candidate's career timeline."""
    rows = await session.scalars(
        select(CareerEvent).where(CareerEvent.candidate_id == candidate_id)
    )
    return list(rows)


async def candidate_skills(
    session: AsyncSession, *, candidate_id: uuid.UUID
) -> list[CandidateSkill]:
    """A candidate's skills."""
    rows = await session.scalars(
        select(CandidateSkill).where(CandidateSkill.candidate_id == candidate_id)
    )
    return list(rows)


async def credentials_for_candidate(
    session: AsyncSession, *, candidate_id: uuid.UUID
) -> list[Credential]:
    """A candidate's credentials."""
    rows = await session.scalars(
        select(Credential).where(Credential.holder_candidate_id == candidate_id)
    )
    return list(rows)


async def count_owned_rows(session: AsyncSession, *, candidate_id: uuid.UUID) -> dict[str, int]:
    """Count candidate-owned rows for the erasure receipt."""
    counts: dict[str, int] = {}
    for label, model, col in (
        ("career_events", CareerEvent, CareerEvent.candidate_id),
        ("skills", CandidateSkill, CandidateSkill.candidate_id),
        ("consent_grants", ConsentGrant, ConsentGrant.candidate_id),
        ("credentials", Credential, Credential.holder_candidate_id),
    ):
        counts[label] = int(
            await session.scalar(select(func.count()).select_from(model).where(col == candidate_id))
            or 0
        )
    return counts


async def delete_candidate_owned(session: AsyncSession, *, candidate_id: uuid.UUID) -> None:
    """Delete candidate-owned career rows. Profile delete cascades the rest."""
    await session.execute(delete(Credential).where(Credential.holder_candidate_id == candidate_id))
    await session.execute(delete(CandidateSkill).where(CandidateSkill.candidate_id == candidate_id))
    await session.execute(delete(CareerEvent).where(CareerEvent.candidate_id == candidate_id))
    await session.execute(delete(ConsentGrant).where(ConsentGrant.candidate_id == candidate_id))
    await session.execute(delete(CandidateProfile).where(CandidateProfile.id == candidate_id))
