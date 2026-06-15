"""Matching endpoints — thin HTTP layer over the matching service.

- ``GET /matching/jobs``        candidate → their top explained job matches
- ``GET /matching/candidates``  employer  → consent-gated explained candidate matches
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    Principal,
    get_session,
    require_roles,
)
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.roles import EMPLOYER_ROLES, Role
from app.domains.admin.audit import record_audit
from app.domains.ai.llm.factory import get_llm
from app.domains.matching import service
from app.domains.matching.repository import MatchingRepository
from app.domains.matching.schemas import (
    CandidateMatch,
    CandidateSummary,
    JobBrief,
    JobMatch,
    SubScores,
)

router = APIRouter(prefix="/matching", tags=["matching"])


@router.get("/jobs", response_model=list[JobMatch])
async def my_job_matches(
    limit: int = Query(10, ge=1, le=50),
    principal: Principal = Depends(require_roles(Role.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> list[JobMatch]:
    """Top explained job matches for the signed-in candidate."""
    repo = MatchingRepository(session)
    candidate = await repo.get_candidate_by_user(uuid.UUID(principal.user_id))
    if candidate is None:
        raise NotFoundError("Candidate profile not found.")

    llm = get_llm()
    results = await service.top_job_matches(
        session,
        candidate=candidate,
        llm=llm,
        limit=limit,
        user_id=principal.user_id,
    )
    return [
        JobMatch(
            job=JobBrief.model_validate(_job_to_brief(r["job"])),
            score=r["score"],
            sub_scores=SubScores(**r["sub_scores"]),
            glass_box=r["glass_box"],
        )
        for r in results
    ]


@router.get("/candidates", response_model=list[CandidateMatch])
async def candidate_matches_for_job(
    job_id: uuid.UUID = Query(..., description="Job to match candidates against."),
    q: str | None = Query(None, description="Optional keyword filter."),
    limit: int = Query(10, ge=1, le=50),
    principal: Principal = Depends(require_roles(*EMPLOYER_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> list[CandidateMatch]:
    """Consent-gated, trajectory-aware candidate matches for an employer's job."""
    if not principal.org_id:
        raise ForbiddenError("This action requires an organization context.")

    repo = MatchingRepository(session)
    job = await repo.get_job(job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    # BOLA defence: an employer may only match against their own org's jobs.
    if not principal.is_platform_admin and str(job.org_id) != principal.org_id:
        raise ForbiddenError("You may only match candidates against your own jobs.")

    llm = get_llm()
    org_uuid = uuid.UUID(principal.org_id)
    matched = await service.candidates_for_job(
        session,
        job=job,
        org_id=org_uuid,
        query=q,
        llm=llm,
        limit=limit,
        user_id=principal.user_id,
    )

    await record_audit(
        session,
        action="matching.candidates.view",
        resource_type="job",
        actor_id=principal.user_id,
        org_id=principal.org_id,
        resource_id=str(job_id),
        detail={"returned": len(matched), "query": q},
    )
    await session.commit()

    names = await repo.candidate_names([c.id for c, _g, _r in matched])

    out: list[CandidateMatch] = []
    for candidate, has_grant, result in matched:
        top_skills = await repo.candidate_skill_names(candidate.id)
        consent_note = (
            "Shown under this candidate's active consent grant. Contact details "
            "unlock only with their explicit opt-in."
            if has_grant
            else "Discoverable because this candidate is open to work. "
            "Request consent to view their full Career Graph."
        )
        out.append(
            CandidateMatch(
                candidate_summary=CandidateSummary(
                    id=str(candidate.id),
                    full_name=names.get(candidate.id) or "Candidate",
                    headline=candidate.headline,
                    current_role=candidate.headline,
                    location=candidate.location,
                    years_experience=candidate.years_experience,
                    open_to_work=candidate.open_to_work,
                    top_skills=top_skills[:8],
                    consent_basis="consent_grant" if has_grant else "open_to_work",
                ),
                score=result["score"],
                sub_scores=SubScores(**result["sub_scores"]),
                glass_box=result["glass_box"],
                consent_note=consent_note,
            )
        )
    return out


def _job_to_brief(job) -> dict:
    """Project an ORM ``Job`` to the candidate-facing brief shape (string ids)."""
    return {
        "id": str(job.id),
        "title": job.title,
        "org_id": str(job.org_id),
        "location": job.location,
        "work_mode": job.work_mode,
        "seniority": job.seniority,
        "comp_min": job.comp_min,
        "comp_max": job.comp_max,
        "currency": job.currency,
    }
