"""University Outcomes Studio endpoints — thin HTTP layer, all org-scoped.

Guards require a university role and an org context; the acting org is always the
principal's org (BOLA-safe). Student readiness verifies the student belongs to
the caller's org before returning anything.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_session, require_roles
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.core.roles import Role
from app.domains.ai.llm.factory import get_llm
from app.domains.universities.repository import UniversityRepository
from app.domains.universities.schemas import (
    CurriculumReport,
    InternshipCreate,
    InternshipRead,
    OutcomesReport,
    ReadinessProfile,
    StudentRoster,
    UniversityDashboard,
)
from app.domains.universities.service import UniversityService

router = APIRouter(prefix="/universities", tags=["universities"])

_university_guard = require_roles(Role.UNIVERSITY_STAFF, Role.UNIVERSITY_ADMIN)


def _service(session: AsyncSession) -> UniversityService:
    return UniversityService(UniversityRepository(session), get_llm())


def _org_uuid(principal: Principal) -> uuid.UUID:
    if not principal.org_id:
        raise ForbiddenError("This action requires a university organization context.")
    return uuid.UUID(principal.org_id)


def _parse_uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValidationError(f"Invalid {field}.") from exc


@router.get("/me/dashboard", response_model=UniversityDashboard)
async def get_dashboard(
    principal: Principal = Depends(_university_guard),
    session: AsyncSession = Depends(get_session),
) -> UniversityDashboard:
    """Headline outcome stats for the university."""
    return await _service(session).dashboard(_org_uuid(principal))


@router.get("/outcomes", response_model=OutcomesReport)
async def get_outcomes(
    cohort: str | None = None,
    year: int | None = None,
    principal: Principal = Depends(_university_guard),
    session: AsyncSession = Depends(get_session),
) -> OutcomesReport:
    """Graduate-outcome analytics, optionally filtered by cohort and/or year."""
    cohort_id = _parse_uuid(cohort, "cohort") if cohort else None
    return await _service(session).outcomes(_org_uuid(principal), cohort_id, year)


@router.get("/students", response_model=StudentRoster)
async def get_students(
    principal: Principal = Depends(_university_guard),
    session: AsyncSession = Depends(get_session),
) -> StudentRoster:
    """Roster of cohort students with a computed readiness score."""
    return await _service(session).students(_org_uuid(principal))


@router.get("/students/{candidate_id}/readiness", response_model=ReadinessProfile)
async def get_readiness(
    candidate_id: str,
    principal: Principal = Depends(_university_guard),
    session: AsyncSession = Depends(get_session),
) -> ReadinessProfile:
    """Adaptive Readiness Profile for a student in the caller's org."""
    cand = _parse_uuid(candidate_id, "candidate_id")
    profile = await _service(session).readiness(_org_uuid(principal), cand, principal.user_id)
    if profile is None:
        raise NotFoundError("Student not found in your organization.")
    return profile


@router.get("/curriculum", response_model=CurriculumReport)
async def get_curriculum(
    principal: Principal = Depends(_university_guard),
    session: AsyncSession = Depends(get_session),
) -> CurriculumReport:
    """Future-State Curriculum: cohort skill coverage vs rising market demand."""
    return await _service(session).curriculum(_org_uuid(principal), principal.user_id)


@router.get("/internships", response_model=list[InternshipRead])
async def list_internships(
    principal: Principal = Depends(_university_guard),
    session: AsyncSession = Depends(get_session),
) -> list[InternshipRead]:
    """List internship listings owned by the caller's org."""
    return await _service(session).list_internships(_org_uuid(principal))


@router.post(
    "/internships",
    response_model=InternshipRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_internship(
    payload: InternshipCreate,
    principal: Principal = Depends(_university_guard),
    session: AsyncSession = Depends(get_session),
) -> InternshipRead:
    """Create an internship listing for the caller's org."""
    return await _service(session).create_internship(_org_uuid(principal), payload)
