"""Thin HTTP layer for the jobs domain. Delegates all logic to the service."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_session, require_roles
from app.core.roles import Role
from app.core.schemas import Page, PageParams
from app.domains.applications.schemas import PipelineEntry
from app.domains.jobs import service
from app.domains.jobs.schemas import (
    JobCreate,
    JobDebiasResult,
    JobMatchRead,
    JobRead,
    JobUpdate,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])

_EMPLOYER = require_roles(Role.EMPLOYER_RECRUITER, Role.EMPLOYER_ADMIN)


@router.get("", response_model=Page[JobRead])
async def search_jobs(
    q: str | None = Query(default=None),
    location: str | None = Query(default=None),
    seniority: str | None = Query(default=None),
    work_mode: str | None = Query(default=None),
    semantic: bool = Query(default=False),
    page: PageParams = Depends(),
    session: AsyncSession = Depends(get_session),
) -> Page[JobRead]:
    """Search open jobs (keyword+facets, or hybrid vector+keyword RRF)."""
    return await service.search_jobs(
        session,
        q=q,
        location=location,
        seniority=seniority,
        work_mode=work_mode,
        semantic=semantic,
        page=page,
    )


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> JobRead:
    """Job detail (increments the view counter)."""
    return await service.get_job(session, job_id)


@router.get("/{job_id}/match", response_model=JobMatchRead)
async def match_job(
    job_id: uuid.UUID,
    principal: Principal = Depends(require_roles(Role.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> JobMatchRead:
    """Explained match between the calling candidate and this job."""
    return await service.match_job(session, principal, job_id)


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    principal: Principal = Depends(_EMPLOYER),
    session: AsyncSession = Depends(get_session),
) -> JobRead:
    """Create a job posting for the employer's organization."""
    return await service.create_job(session, principal, payload)


@router.put("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    principal: Principal = Depends(_EMPLOYER),
    session: AsyncSession = Depends(get_session),
) -> JobRead:
    """Update a job (same-org only)."""
    return await service.update_job(session, principal, job_id, payload)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: uuid.UUID,
    principal: Principal = Depends(_EMPLOYER),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a job (same-org only)."""
    await service.delete_job(session, principal, job_id)


@router.post("/{job_id}/debias", response_model=JobDebiasResult)
async def debias_job(
    job_id: uuid.UUID,
    principal: Principal = Depends(_EMPLOYER),
    session: AsyncSession = Depends(get_session),
) -> JobDebiasResult:
    """Bias Auditor: rewrite the JD and flag exclusionary language."""
    return await service.debias_job(session, principal, job_id)


@router.get("/{job_id}/applications", response_model=list[PipelineEntry])
async def job_pipeline(
    job_id: uuid.UUID,
    principal: Principal = Depends(_EMPLOYER),
    session: AsyncSession = Depends(get_session),
) -> list[PipelineEntry]:
    """Application pipeline for a job (same-org employers only)."""
    return await service.job_pipeline(session, principal, job_id)
