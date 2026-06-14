"""Consent + data-dignity business logic (grants, revoke, access log, export, erase).

A candidate owns their career graph. This service lets them grant/revoke scoped,
time-boxed access, see who viewed their record, export everything (portability),
and erase their data (right-to-erasure) — every privileged action is audited.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.domains.consent import repository as repo
from app.domains.consent.models import ConsentGrant
from app.domains.consent.schemas import (
    AccessLogEntry,
    ConsentCreate,
    ConsentRead,
    DataExport,
    ErasureResult,
)

try:  # Optional cross-domain dependency; degrade gracefully if unavailable.
    from app.domains.admin.audit import record_audit
except ImportError:  # pragma: no cover
    record_audit = None  # type: ignore[assignment]


async def _require_candidate_id(session: AsyncSession, *, user_id: str) -> uuid.UUID:
    """Resolve the calling user's candidate profile id or 404."""
    profile = await repo.candidate_for_user(session, user_id=uuid.UUID(user_id))
    if profile is None:
        raise NotFoundError("Candidate profile not found.")
    return profile.id


async def _audit(session: AsyncSession, **kwargs) -> None:
    if record_audit is not None:
        await record_audit(session, **kwargs)


async def list_grants(session: AsyncSession, *, user_id: str) -> list[ConsentRead]:
    """My consent grants (active and past)."""
    candidate_id = await _require_candidate_id(session, user_id=user_id)
    rows = await repo.list_grants(session, candidate_id=candidate_id)
    return [ConsentRead.model_validate(r) for r in rows]


async def create_grant(
    session: AsyncSession, *, user_id: str, payload: ConsentCreate
) -> ConsentRead:
    """Grant a scoped, optionally time-boxed access to an org."""
    candidate_id = await _require_candidate_id(session, user_id=user_id)
    grant = ConsentGrant(
        candidate_id=candidate_id,
        grantee_org_id=payload.grantee_org_id,
        scopes=payload.scopes,
        purpose=payload.purpose,
        expires_at=payload.expires_at,
    )
    await repo.add_grant(session, grant)
    await _audit(
        session,
        action="consent.granted",
        resource_type="candidate",
        actor_id=user_id,
        resource_id=str(candidate_id),
        detail={"grantee_org_id": str(payload.grantee_org_id), "scopes": payload.scopes},
    )
    await session.commit()
    await session.refresh(grant)
    return ConsentRead.model_validate(grant)


async def revoke_grant(session: AsyncSession, *, user_id: str, grant_id: uuid.UUID) -> ConsentRead:
    """Revoke a grant I own (sets ``revoked_at``)."""
    candidate_id = await _require_candidate_id(session, user_id=user_id)
    grant = await repo.get_grant_for_candidate(
        session, grant_id=grant_id, candidate_id=candidate_id
    )
    if grant is None:
        raise NotFoundError("Consent grant not found.")
    if grant.revoked_at is not None:
        raise ConflictError("Consent grant is already revoked.")
    grant.revoked_at = datetime.now(UTC)
    await _audit(
        session,
        action="consent.revoked",
        resource_type="candidate",
        actor_id=user_id,
        resource_id=str(candidate_id),
        detail={"grant_id": str(grant_id)},
    )
    await session.commit()
    await session.refresh(grant)
    return ConsentRead.model_validate(grant)


async def access_log(session: AsyncSession, *, user_id: str) -> list[AccessLogEntry]:
    """Who viewed my candidate record (from the audit log)."""
    candidate_id = await _require_candidate_id(session, user_id=user_id)
    rows = await repo.access_log_for_candidate(session, candidate_id=candidate_id)
    return [AccessLogEntry.model_validate(r, from_attributes=True) for r in rows]


def _row_to_dict(obj) -> dict:
    """Serialise an ORM row's columns to JSON-friendly primitives."""
    out: dict = {}
    for col in obj.__table__.columns:
        value = getattr(obj, col.name)
        if isinstance(value, (uuid.UUID, datetime)):
            out[col.name] = str(value)
        else:
            out[col.name] = value
    return out


async def export_data(session: AsyncSession, *, user_id: str) -> DataExport:
    """Full JSON export of my identity + career data (portability)."""
    uid = uuid.UUID(user_id)
    user = await repo.get_user(session, user_id=uid)
    if user is None:
        raise NotFoundError("User not found.")
    profile = await repo.candidate_for_user(session, user_id=uid)

    user_dict = _row_to_dict(user)
    user_dict.pop("hashed_password", None)

    candidate_dict = None
    events: list[dict] = []
    skills: list[dict] = []
    grants: list[dict] = []
    creds: list[dict] = []
    if profile is not None:
        candidate_dict = _row_to_dict(profile)
        candidate_dict.pop("embedding", None)
        events = [
            _row_to_dict(e) for e in await repo.career_events(session, candidate_id=profile.id)
        ]
        skills = [
            _row_to_dict(s) for s in await repo.candidate_skills(session, candidate_id=profile.id)
        ]
        grants = [_row_to_dict(g) for g in await repo.list_grants(session, candidate_id=profile.id)]
        creds = [
            _row_to_dict(c)
            for c in await repo.credentials_for_candidate(session, candidate_id=profile.id)
        ]

    await _audit(
        session,
        action="data.exported",
        resource_type="candidate",
        actor_id=user_id,
        resource_id=str(profile.id) if profile else None,
    )
    await session.commit()

    return DataExport(
        exported_at=datetime.now(UTC),
        user=user_dict,
        candidate=candidate_dict,
        career_events=events,
        skills=skills,
        consent_grants=grants,
        credentials=creds,
    )


async def erase_data(session: AsyncSession, *, user_id: str) -> ErasureResult:
    """Right-to-erasure: delete candidate-owned rows, keep an audit entry."""
    uid = uuid.UUID(user_id)
    profile = await repo.candidate_for_user(session, user_id=uid)
    if profile is None:
        # Nothing career-side to erase, but still record the request.
        await _audit(
            session,
            action="data.erased",
            resource_type="candidate",
            actor_id=user_id,
            resource_id=None,
            detail={"note": "no candidate profile"},
        )
        await session.commit()
        return ErasureResult(erased=True, deleted_counts={})

    counts = await repo.count_owned_rows(session, candidate_id=profile.id)
    await repo.delete_candidate_owned(session, candidate_id=profile.id)
    # Audit entry is intentionally retained for accountability after erasure.
    await _audit(
        session,
        action="data.erased",
        resource_type="candidate",
        actor_id=user_id,
        resource_id=str(profile.id),
        detail={"deleted_counts": counts},
    )
    await session.commit()
    return ErasureResult(erased=True, deleted_counts=counts)
