"""Signal business logic + a public ``create_signal`` helper for other modules."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.schemas import Page
from app.domains.ai.schemas import (
    Citation,
    CitationSourceType,
    Confidence,
    GlassBox,
)
from app.domains.signals import repository as repo
from app.domains.signals.models import SIGNAL_TYPES, Signal
from app.domains.signals.schemas import SignalEvidence, SignalRead, is_valid_type

# Human-readable titles per signal type.
_SIGNAL_TITLES = {
    "activity_drop": "Engagement drop",
    "peer_departure": "Peer departures",
    "profile_update": "Profile refresh",
    "underpaid": "Below-market pay",
    "plateau": "Career plateau",
    "onboarding_risk": "Onboarding risk",
    "open_role_fit": "Open-role fit",
    "skill_decay": "Skill decay",
}


def _severity(strength: float) -> str:
    return "high" if strength >= 0.75 else "medium" if strength >= 0.5 else "low"


def _evidence_rows(evidence: dict[str, Any] | None) -> list[SignalEvidence]:
    """Flatten the evidence JSON blob into labelled rows for the UI."""
    rows: list[SignalEvidence] = []
    for key, value in (evidence or {}).items():
        label = key.replace("_", " ").title()
        rows.append(SignalEvidence(label=label, detail=str(value)))
    return rows


def _signal_glass_box(signal: Signal) -> GlassBox:
    """A deterministic, honest Glass Box for a quiet signal (no LLM)."""
    band = (
        Confidence.HIGH
        if signal.strength >= 0.75
        else Confidence.MEDIUM
        if signal.strength >= 0.5
        else Confidence.LOW
    )
    title = _SIGNAL_TITLES.get(signal.type, signal.type.replace("_", " ").title())
    return GlassBox(
        rationale=(
            f"{title}: {signal.summary or 'observed against the cohort baseline'}. "
            "This is an early, supportive flag — not a verdict."
        ),
        confidence=band,
        confidence_score=round(min(0.95, max(0.2, float(signal.strength))), 2),
        citations=[
            Citation(
                label="Observed engagement signals",
                source_type=CitationSourceType.CAREER_HISTORY,
                source_id=str(signal.subject_candidate_id),
            )
        ],
        what_would_change_this=[
            "A manager check-in confirming engagement",
            "A fresh role change or new verified skill",
        ],
        caveats=["Signals are probabilistic; act with context and consent."],
    )


def _to_read(signal: Signal, subject_name: str | None = None) -> SignalRead:
    return SignalRead(
        id=str(signal.id),
        type=signal.type,
        subject_candidate_id=str(signal.subject_candidate_id),
        subject_name=subject_name,
        title=_SIGNAL_TITLES.get(signal.type, signal.type.replace("_", " ").title()),
        summary=signal.summary,
        severity=_severity(float(signal.strength)),
        status=signal.status,
        evidence=_evidence_rows(signal.evidence),
        glass_box=_signal_glass_box(signal),
        detected_at=signal.created_at,
    )


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
    names = await repo.subject_names(session, [r.subject_candidate_id for r in rows])
    return Page[SignalRead](
        items=[_to_read(r, names.get(r.subject_candidate_id)) for r in rows],
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
    names = await repo.subject_names(session, [signal.subject_candidate_id])
    return _to_read(signal, names.get(signal.subject_candidate_id))
