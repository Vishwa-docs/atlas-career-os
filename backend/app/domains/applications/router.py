"""Thin HTTP layer for the applications domain."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_session, require_roles
from app.core.roles import Role
from app.domains.applications import service
from app.domains.applications.schemas import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationStatusUpdate,
    CandidateApplicationRow,
)

router = APIRouter(prefix="/applications", tags=["applications"])

_CANDIDATE = require_roles(Role.CANDIDATE)
_EMPLOYER = require_roles(Role.EMPLOYER_RECRUITER, Role.EMPLOYER_ADMIN)


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def apply(
    payload: ApplicationCreate,
    principal: Principal = Depends(_CANDIDATE),
    session: AsyncSession = Depends(get_session),
) -> ApplicationRead:
    """Candidate applies to a job."""
    return await service.apply(session, principal, payload)


@router.get("", response_model=list[CandidateApplicationRow])
async def list_my_applications(
    principal: Principal = Depends(_CANDIDATE),
    session: AsyncSession = Depends(get_session),
) -> list[CandidateApplicationRow]:
    """The calling candidate's applications as flat cards with a status timeline."""
    return await service.list_my_applications(session, principal)


@router.patch("/{application_id}/status", response_model=ApplicationRead)
async def update_status(
    application_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
    principal: Principal = Depends(_EMPLOYER),
    session: AsyncSession = Depends(get_session),
) -> ApplicationRead:
    """Employer advances an application (same org as the job)."""
    return await service.update_status(session, principal, application_id, payload)
