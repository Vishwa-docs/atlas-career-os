"""Candidate Navigator HTTP routes (thin).

Mounted under ``/api/v1`` by the aggregator, so ``prefix="/candidates"`` yields
``/api/v1/candidates``. Business logic lives in :mod:`service`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    Principal,
    get_current_principal,
    get_session,
    require_roles,
)
from app.core.exceptions import ValidationError
from app.core.roles import Role
from app.domains.candidates.schemas import (
    CandidateDashboard,
    CandidateMe,
    CandidateProfileUpdate,
    CandidatePublic,
    CandidateSkillRead,
    CareerEventCreate,
    CareerEventRead,
    CareerEventUpdate,
    ResumeParse,
    ResumeRequest,
    SkillsReplace,
)
from app.domains.candidates.service import CandidateService

# Optional cross-domain audit; degrade gracefully if unavailable.
try:  # pragma: no cover - defensive import
    from app.domains.admin.audit import record_audit
except ImportError:  # pragma: no cover
    record_audit = None  # type: ignore[assignment]

router = APIRouter(prefix="/candidates", tags=["candidates"])


def _service(session: AsyncSession) -> CandidateService:
    return CandidateService(session)


# --------------------------------------------------------------------------- #
# /me
# --------------------------------------------------------------------------- #


@router.get("/me", response_model=CandidateMe)
async def get_my_profile(
    principal: Principal = Depends(require_roles(Role.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> CandidateMe:
    """Return my profile, career timeline, skills, and completeness."""
    return await _service(session).get_me(principal.user_id)


@router.put("/me", response_model=CandidateMe)
async def update_my_profile(
    payload: CandidateProfileUpdate,
    principal: Principal = Depends(require_roles(Role.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> CandidateMe:
    """Update profile fields; recompute completeness + embedding."""
    return await _service(session).update_me(principal.user_id, payload)


@router.post("/me/resume/parse", response_model=ResumeParse)
async def parse_resume(
    body: ResumeRequest | None = None,
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    principal: Principal = Depends(require_roles(Role.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> ResumeParse:
    """Parse a resume (JSON ``{text}`` or multipart upload) into a structured preview."""
    resume_text: str | None = None
    if body is not None and body.text:
        resume_text = body.text
    elif text:
        resume_text = text
    elif file is not None:
        raw = await file.read()
        resume_text = raw.decode("utf-8", errors="ignore")
    if not resume_text or not resume_text.strip():
        raise ValidationError("Provide resume text via JSON {text} or a file upload.")
    return await _service(session).parse_resume(principal.user_id, resume_text)


# --------------------------------------------------------------------------- #
# Career events
# --------------------------------------------------------------------------- #


@router.post("/me/career-events", response_model=CareerEventRead, status_code=201)
async def create_career_event(
    payload: CareerEventCreate,
    principal: Principal = Depends(require_roles(Role.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> CareerEventRead:
    return await _service(session).create_career_event(principal.user_id, payload)


@router.put("/me/career-events/{event_id}", response_model=CareerEventRead)
async def update_career_event(
    event_id: str,
    payload: CareerEventUpdate,
    principal: Principal = Depends(require_roles(Role.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> CareerEventRead:
    return await _service(session).update_career_event(principal.user_id, event_id, payload)


@router.delete("/me/career-events/{event_id}", status_code=204)
async def delete_career_event(
    event_id: str,
    principal: Principal = Depends(require_roles(Role.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _service(session).delete_career_event(principal.user_id, event_id)


# --------------------------------------------------------------------------- #
# Skills
# --------------------------------------------------------------------------- #


@router.get("/me/skills", response_model=list[CandidateSkillRead])
async def get_my_skills(
    principal: Principal = Depends(require_roles(Role.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> list[CandidateSkillRead]:
    return await _service(session).get_skills(principal.user_id)


@router.put("/me/skills", response_model=list[CandidateSkillRead])
async def replace_my_skills(
    payload: SkillsReplace,
    principal: Principal = Depends(require_roles(Role.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> list[CandidateSkillRead]:
    return await _service(session).replace_skills(principal.user_id, payload)


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #


@router.get("/me/dashboard", response_model=CandidateDashboard)
async def get_my_dashboard(
    principal: Principal = Depends(require_roles(Role.CANDIDATE)),
    session: AsyncSession = Depends(get_session),
) -> CandidateDashboard:
    return await _service(session).get_dashboard(principal.user_id)


# --------------------------------------------------------------------------- #
# Public (employer / university) — consent-gated
# --------------------------------------------------------------------------- #


@router.get("/{candidate_id}", response_model=CandidatePublic)
async def get_candidate(
    candidate_id: str,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> CandidatePublic:
    """Consent-gated external view of a candidate; logged to the audit trail."""
    service = _service(session)
    result = await service.get_public_candidate(
        candidate_id,
        viewer_org_id=principal.org_id,
        is_platform_admin=principal.is_platform_admin,
    )
    if record_audit is not None:
        try:
            await record_audit(
                session,
                action="view_candidate",
                resource_type="candidate",
                actor_id=principal.user_id,
                org_id=principal.org_id,
                resource_id=candidate_id,
            )
            await session.commit()
        except Exception:  # pragma: no cover - audit is best-effort
            await session.rollback()
    return result
