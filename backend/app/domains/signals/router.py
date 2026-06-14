"""Thin HTTP layer for signals (employer-facing, org-scoped)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_session, require_org, require_roles
from app.core.roles import Role
from app.core.schemas import Page, PageParams
from app.domains.signals import service
from app.domains.signals.schemas import SignalRead, SignalStatusUpdate

router = APIRouter(prefix="/signals", tags=["signals"])

_EMPLOYER = require_roles(Role.EMPLOYER_RECRUITER, Role.EMPLOYER_ADMIN)


@router.get("", response_model=Page[SignalRead])
async def list_signals(
    type: str | None = Query(None),
    status: str | None = Query(None),
    params: PageParams = Depends(PageParams),
    principal: Principal = Depends(_EMPLOYER),
    session: AsyncSession = Depends(get_session),
) -> Page[SignalRead]:
    """Retention/onboarding signals for the caller's organization, with evidence."""
    require_org(principal)
    return await service.list_signals(
        session,
        org_id=principal.org_id,  # type: ignore[arg-type]
        type=type,
        status=status,
        offset=params.offset,
        limit=params.limit,
        page=params.page,
        page_size=params.page_size,
    )


@router.patch("/{signal_id}", response_model=SignalRead)
async def update_signal(
    signal_id: str,
    body: SignalStatusUpdate,
    principal: Principal = Depends(_EMPLOYER),
    session: AsyncSession = Depends(get_session),
) -> SignalRead:
    """Acknowledge / action / dismiss a signal (org-scoped)."""
    require_org(principal)
    return await service.update_status(
        session,
        signal_id=uuid.UUID(signal_id),
        org_id=principal.org_id,  # type: ignore[arg-type]
        status=body.status,
    )
