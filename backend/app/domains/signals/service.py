"""Signal business logic + a public ``create_signal`` helper for other modules."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.schemas import Page
from app.domains.signals import repository as repo
from app.domains.signals.models import SIGNAL_TYPES, Signal
from app.domains.signals.schemas import SignalRead, is_valid_type


async def create_signal(
    session: AsyncSession,
    *,
    subject_candidate_id: str | uuid.UUID,
    type: str,
    org_id: str | uuid.UUID | None = None,
    strength: float = 0.5,
    summary: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> Signal:
    """Create a quiet signal. Flushes, does not commit.

    Exported for other modules (matching, employers, AI nudges) to raise signals
    within their own transaction.
    """
    if not is_valid_type(type):
        raise ValidationError(f"type must be one of {SIGNAL_TYPES}")
    return await repo.add(
        session,
        subject_candidate_id=uuid.UUID(str(subject_candidate_id)),
        org_id=uuid.UUID(str(org_id)) if org_id else None,
        type=type,
        strength=max(0.0, min(1.0, strength)),
        summary=summary,
        evidence=evidence,
    )


async def list_signals(
    session: AsyncSession,
    *,
    org_id: str,
    type: str | None,
    status: str | None,
    offset: int,
    limit: int,
    page: int,
    page_size: int,
) -> Page[SignalRead]:
    """List an org's signals (strongest first), optionally filtered."""
    rows, total = await repo.list_for_org(
        session,
        org_id=uuid.UUID(org_id),
        type=type,
        status=status,
        offset=offset,
        limit=limit,
    )
    return Page[SignalRead](
        items=[SignalRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def update_status(
    session: AsyncSession, *, signal_id: uuid.UUID, org_id: str, status: str
) -> SignalRead:
    """Transition an org-owned signal to a new status."""
    signal = await repo.get_for_org(session, signal_id=signal_id, org_id=uuid.UUID(org_id))
    if signal is None:
        raise NotFoundError("Signal not found.")
    signal.status = status
    await session.commit()
    await session.refresh(signal)
    return SignalRead.model_validate(signal)
