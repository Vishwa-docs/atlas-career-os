"""Thin HTTP layer for consent + data-dignity (candidate-facing)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_current_principal, get_session
from app.domains.consent import service
from app.domains.consent.schemas import (
    AccessLogEntry,
    ConsentCreate,
    ConsentRead,
    DataExport,
    ErasureResult,
)

router = APIRouter(prefix="/consent", tags=["consent"])


@router.get("", response_model=list[ConsentRead])
async def list_grants(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[ConsentRead]:
    """My consent grants — active and past."""
    return await service.list_grants(session, user_id=principal.user_id)


@router.post("", response_model=ConsentRead, status_code=status.HTTP_201_CREATED)
async def create_grant(
    body: ConsentCreate,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ConsentRead:
    """Grant an organization scoped, time-boxed access to my data."""
    return await service.create_grant(session, user_id=principal.user_id, payload=body)


@router.get("/access-log", response_model=list[AccessLogEntry])
async def access_log(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[AccessLogEntry]:
    """Who viewed my candidate record (from the audit log)."""
    return await service.access_log(session, user_id=principal.user_id)


@router.get("/export", response_model=DataExport)
async def export_data(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> DataExport:
    """Full JSON export of my identity + career data (portability)."""
    return await service.export_data(session, user_id=principal.user_id)


@router.delete("/erase", response_model=ErasureResult)
async def erase_data(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ErasureResult:
    """Right-to-erasure: delete my candidate-owned data."""
    return await service.erase_data(session, user_id=principal.user_id)


@router.delete("/{grant_id}", response_model=ConsentRead)
async def revoke_grant(
    grant_id: str,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ConsentRead:
    """Revoke a grant I own."""
    return await service.revoke_grant(
        session, user_id=principal.user_id, grant_id=uuid.UUID(grant_id)
    )
