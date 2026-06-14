"""Organization endpoints (thin). Mounted at /api/v1/organizations."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_current_principal, get_session
from app.domains.organizations.repository import OrganizationRepository
from app.domains.organizations.schemas import OrganizationRead, OrganizationUpdate
from app.domains.organizations.service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _service(session: AsyncSession) -> OrganizationService:
    return OrganizationService(OrganizationRepository(session))


@router.get("/me", response_model=OrganizationRead)
async def my_organization(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> OrganizationRead:
    """The current user's organization."""
    return await _service(session).get_my_org(principal)


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_organization(
    org_id: str,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> OrganizationRead:
    return await _service(session).get_org(org_id, principal)


@router.put("/{org_id}", response_model=OrganizationRead)
async def update_organization(
    org_id: str,
    body: OrganizationUpdate,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> OrganizationRead:
    """Org-admin-only update, scoped to the actor's own organization."""
    return await _service(session).update_org(org_id, body, principal)
