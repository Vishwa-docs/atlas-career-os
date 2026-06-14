"""Thin HTTP layer for credentials."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_current_principal, get_session, require_roles
from app.core.roles import Role
from app.domains.credentials import service
from app.domains.credentials.schemas import (
    CredentialIssue,
    CredentialRead,
    CredentialVerification,
)

router = APIRouter(prefix="/credentials", tags=["credentials"])

_ISSUER = require_roles(Role.UNIVERSITY_STAFF, Role.UNIVERSITY_ADMIN)


@router.post("", response_model=CredentialRead, status_code=status.HTTP_201_CREATED)
async def issue_credential(
    body: CredentialIssue,
    principal: Principal = Depends(_ISSUER),
    session: AsyncSession = Depends(get_session),
) -> CredentialRead:
    """Issue and mock-sign a verifiable credential for a candidate."""
    return await service.issue_credential(session, issuer_org_id=principal.org_id, payload=body)


@router.get("/me", response_model=list[CredentialRead])
async def my_credentials(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[CredentialRead]:
    """The calling candidate's wallet of credentials."""
    return await service.list_my_credentials(session, user_id=principal.user_id)


@router.get("/verify/{credential_id}", response_model=CredentialVerification)
async def verify_credential(
    credential_id: str,
    session: AsyncSession = Depends(get_session),
) -> CredentialVerification:
    """Recompute the proof and report whether the credential is intact."""
    return await service.verify_credential(session, credential_id=uuid.UUID(credential_id))
