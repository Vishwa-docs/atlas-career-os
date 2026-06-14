"""Admin Mission Control endpoints (thin). Mounted at /api/v1/admin.

Every route requires the platform admin role.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_session, require_roles
from app.core.roles import Role
from app.core.schemas import Page, PageParams
from app.domains.admin.repository import AdminRepository
from app.domains.admin.schemas import (
    AdminUserRead,
    AiUsageReport,
    AuditLogRead,
    PlatformMetrics,
    TaxonomyCounts,
    TenantRead,
)
from app.domains.admin.service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])

_require_admin = require_roles(Role.PLATFORM_ADMIN)


def _service(session: AsyncSession) -> AdminService:
    return AdminService(AdminRepository(session))


@router.get("/metrics", response_model=PlatformMetrics)
async def metrics(
    _: Principal = Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
) -> PlatformMetrics:
    return await _service(session).metrics()


@router.get("/tenants", response_model=Page[TenantRead])
async def tenants(
    params: PageParams = Depends(),
    _: Principal = Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
) -> Page[TenantRead]:
    return await _service(session).tenants(params)


@router.get("/users", response_model=Page[AdminUserRead])
async def users(
    params: PageParams = Depends(),
    _: Principal = Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
) -> Page[AdminUserRead]:
    return await _service(session).users(params)


@router.get("/taxonomy", response_model=TaxonomyCounts)
async def taxonomy(
    _: Principal = Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
) -> TaxonomyCounts:
    return await _service(session).taxonomy()


@router.get("/ai-usage", response_model=AiUsageReport)
async def ai_usage(
    _: Principal = Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
) -> AiUsageReport:
    return await _service(session).ai_usage()


@router.get("/audit", response_model=Page[AuditLogRead])
async def audit(
    params: PageParams = Depends(),
    action: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    _: Principal = Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
) -> Page[AuditLogRead]:
    return await _service(session).audit(params, action=action, actor=actor)
