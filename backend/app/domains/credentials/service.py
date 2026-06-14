"""Credential issuance + verification (mock Open Badges 3.0 proof).

The "signature" is a deterministic SHA-256 over the canonical JSON of the
credential's claims — enough to demonstrate tamper-evidence in the demo without
real key management. Verification recomputes the same hash and compares.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.domains.credentials import repository as repo
from app.domains.credentials.models import Credential
from app.domains.credentials.schemas import (
    CredentialIssue,
    CredentialRead,
    CredentialVerification,
    is_valid_type,
)

_PROOF_FORMAT = "OpenBadges3.0-mock"
_PROOF_ALG = "sha256"


def _canonical_claims(
    *,
    issuer_org_id: uuid.UUID | None,
    holder_candidate_id: uuid.UUID,
    type: str,
    title: str,
    skill_slugs: list[str],
    issued_at: datetime | None,
) -> str:
    """Stable, sorted JSON of the signed claims (key order independent)."""
    claims = {
        "issuer": str(issuer_org_id) if issuer_org_id else None,
        "holder": str(holder_candidate_id),
        "type": type,
        "title": title,
        "skills": sorted(skill_slugs),
        "issued_at": issued_at.isoformat() if issued_at else None,
    }
    return json.dumps(claims, sort_keys=True, separators=(",", ":"))


def _sign(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def issue_credential(
    session: AsyncSession,
    *,
    issuer_org_id: str | None,
    payload: CredentialIssue,
) -> CredentialRead:
    """Issue and mock-sign a credential for a candidate."""
    if not is_valid_type(payload.type):
        raise ValidationError("Unknown credential type.")
    if not await repo.candidate_exists(session, candidate_id=payload.holder_candidate_id):
        raise NotFoundError("Holder candidate not found.")

    issuer_uuid = uuid.UUID(issuer_org_id) if issuer_org_id else None
    issued_at = datetime.now(UTC)
    canonical = _canonical_claims(
        issuer_org_id=issuer_uuid,
        holder_candidate_id=payload.holder_candidate_id,
        type=payload.type,
        title=payload.title,
        skill_slugs=payload.skill_slugs,
        issued_at=issued_at,
    )
    proof = {"format": _PROOF_FORMAT, "alg": _PROOF_ALG, "jws": _sign(canonical)}

    credential = Credential(
        issuer_org_id=issuer_uuid,
        holder_candidate_id=payload.holder_candidate_id,
        type=payload.type,
        title=payload.title,
        description=payload.description,
        skill_slugs=payload.skill_slugs,
        proof=proof,
        issued_at=issued_at,
        expires_at=payload.expires_at,
        status="active",
    )
    await repo.add(session, credential)
    await session.commit()
    await session.refresh(credential)
    return CredentialRead.model_validate(credential)


async def verify_credential(
    session: AsyncSession, *, credential_id: uuid.UUID
) -> CredentialVerification:
    """Recompute the proof and report whether the credential is intact."""
    credential = await repo.get(session, credential_id=credential_id)
    if credential is None:
        raise NotFoundError("Credential not found.")

    canonical = _canonical_claims(
        issuer_org_id=credential.issuer_org_id,
        holder_candidate_id=credential.holder_candidate_id,
        type=credential.type,
        title=credential.title,
        skill_slugs=credential.skill_slugs,
        issued_at=credential.issued_at,
    )
    expected = _sign(canonical)
    stored = (credential.proof or {}).get("jws")
    valid = stored == expected and credential.status == "active"

    return CredentialVerification(
        valid=valid,
        issuer=credential.issuer_org_id,
        holder=credential.holder_candidate_id,
        skills=list(credential.skill_slugs or []),
        issued_at=credential.issued_at,
    )


async def list_my_credentials(session: AsyncSession, *, user_id: str) -> list[CredentialRead]:
    """Return the calling candidate's credentials."""
    candidate_id = await repo.candidate_id_for_user(session, user_id=uuid.UUID(user_id))
    if candidate_id is None:
        raise NotFoundError("Candidate profile not found.")
    rows = await repo.list_for_candidate(session, candidate_id=candidate_id)
    return [CredentialRead.model_validate(r) for r in rows]
