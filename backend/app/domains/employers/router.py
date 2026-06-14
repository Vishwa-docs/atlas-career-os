"""Employer cockpit endpoints — thin HTTP layer, all org-scoped.

Guards require an employer role and an org context; every handler resolves the
acting org from the principal (BOLA-safe — no org id is ever taken from the URL).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_session, require_roles
from app.core.exceptions import ForbiddenError
from app.core.roles import Role
from app.domains.ai.llm.factory import get_llm
from app.domains.employers.repository import EmployerRepository
from app.domains.employers.schemas import (
    EmployerDashboard,
    OnboardingReport,
    ReengagementReport,
    WorkforceReport,
)
from app.domains.employers.service import EmployerService

router = APIRouter(prefix="/employers", tags=["employers"])

_employer_guard = require_roles(Role.EMPLOYER_RECRUITER, Role.EMPLOYER_ADMIN)


def _service(session: AsyncSession) -> EmployerService:
    return EmployerService(EmployerRepository(session), get_llm())


def _org_uuid(principal: Principal) -> uuid.UUID:
    if not principal.org_id:
        raise ForbiddenError("This action requires an employer organization context.")
    return uuid.UUID(principal.org_id)


@router.get("/me/dashboard", response_model=EmployerDashboard)
async def get_dashboard(
    principal: Principal = Depends(_employer_guard),
    session: AsyncSession = Depends(get_session),
) -> EmployerDashboard:
    """Hiring cockpit: open roles, pipeline, time-to-fill, flight risk, activity."""
    return await _service(session).dashboard(_org_uuid(principal))


@router.get("/onboarding", response_model=OnboardingReport)
async def get_onboarding(
    principal: Principal = Depends(_employer_guard),
    session: AsyncSession = Depends(get_session),
) -> OnboardingReport:
    """Onboarding Success Predictor — first-60-day risk for recent hires."""
    return await _service(session).onboarding(_org_uuid(principal))


@router.get("/reengagement", response_model=ReengagementReport)
async def get_reengagement(
    principal: Principal = Depends(_employer_guard),
    session: AsyncSession = Depends(get_session),
) -> ReengagementReport:
    """Warm-bench: previously rejected/withdrawn applicants worth re-contacting."""
    return await _service(session).reengagement(_org_uuid(principal))


@router.get("/workforce", response_model=WorkforceReport)
async def get_workforce(
    country: str = "MY",
    principal: Principal = Depends(_employer_guard),
    session: AsyncSession = Depends(get_session),
) -> WorkforceReport:
    """Workforce Resilience: APAC demographic projections + grounded scenarios."""
    return await _service(session).workforce(
        _org_uuid(principal), country=country, user_id=principal.user_id
    )
