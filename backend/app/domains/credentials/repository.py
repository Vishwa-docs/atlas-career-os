"""All DB queries for credentials (async SQLAlchemy 2.0)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.candidates.models import CandidateProfile
from app.domains.credentials.models import Credential


async def add(session: AsyncSession, credential: Credential) -> Credential:
    """Persist a new credential (flushed so the caller gets its id)."""
    session.add(credential)
    await session.flush()
    return credential


async def get(session: AsyncSession, *, credential_id: uuid.UUID) -> Credential | None:
    """Fetch a credential by id."""
    return await session.scalar(select(Credential).where(Credential.id == credential_id))


async def list_for_candidate(session: AsyncSession, *, candidate_id: uuid.UUID) -> list[Credential]:
    """All credentials held by a candidate, newest first."""
    rows = await session.scalars(
        select(Credential)
        .where(Credential.holder_candidate_id == candidate_id)
        .order_by(Credential.created_at.desc())
    )
    return list(rows)


async def candidate_id_for_user(session: AsyncSession, *, user_id: uuid.UUID) -> uuid.UUID | None:
    """Resolve the candidate profile id owned by a user."""
    return await session.scalar(
        select(CandidateProfile.id).where(CandidateProfile.user_id == user_id)
    )


async def candidate_exists(session: AsyncSession, *, candidate_id: uuid.UUID) -> bool:
    """Whether a candidate profile exists."""
    found = await session.scalar(
        select(CandidateProfile.id).where(CandidateProfile.id == candidate_id)
    )
    return found is not None
