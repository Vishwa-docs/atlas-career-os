"""All DB queries for signals (async SQLAlchemy 2.0)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.candidates.models import CandidateProfile
from app.domains.signals.models import Signal
from app.domains.users.models import User


async def add(
    session: AsyncSession,
    *,
    subject_candidate_id: uuid.UUID,
    org_id: uuid.UUID | None,
    type: str,
    strength: float,
    summary: str | None,
    evidence: dict[str, Any] | None,
) -> Signal:
    """Insert a signal (flushed so the caller gets its id)."""
    signal = Signal(
        subject_candidate_id=subject_candidate_id,
        org_id=org_id,
        type=type,
        strength=strength,
        summary=summary,
        evidence=evidence or {},
    )
    session.add(signal)
    await session.flush()
    return signal


async def list_for_org(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    type: str | None,
    status: str | None,
    offset: int,
    limit: int,
) -> tuple[list[Signal], int]:
    """Return a filtered, paginated list of signals for an org and the total."""
    base = select(Signal).where(Signal.org_id == org_id)
    if type is not None:
        base = base.where(Signal.type == type)
    if status is not None:
        base = base.where(Signal.status == status)
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    rows = await session.scalars(
        base.order_by(Signal.strength.desc(), Signal.created_at.desc()).offset(offset).limit(limit)
    )
    return list(rows), int(total or 0)


async def get_for_org(
    session: AsyncSession, *, signal_id: uuid.UUID, org_id: uuid.UUID
) -> Signal | None:
    """Fetch one signal scoped to the org (BOLA defence)."""
    return await session.scalar(
        select(Signal).where(Signal.id == signal_id, Signal.org_id == org_id)
    )


async def subject_names(
    session: AsyncSession, candidate_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """Map candidate-profile id → subject's full name (one batched query)."""
    if not candidate_ids:
        return {}
    stmt = (
        select(CandidateProfile.id, User.full_name)
        .join(User, User.id == CandidateProfile.user_id)
        .where(CandidateProfile.id.in_(candidate_ids))
    )
    rows = (await session.execute(stmt)).all()
    return {cid: name for cid, name in rows if name}
