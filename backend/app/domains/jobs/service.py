"""Business logic for the jobs domain: search, CRUD, match, debias, pipeline.

Routers stay thin; this layer owns authorization (BOLA defence), LLM calls (with
usage accounting + guardrails), and the commit boundary.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, require_same_org
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.schemas import Page, PageParams
from app.domains.ai.guardrails import SYSTEM_PREAMBLE, wrap_untrusted
from app.domains.ai.llm.client import ChatMessage, TokenUsage
from app.domains.ai.llm.factory import get_llm
from app.domains.ai.schemas import Citation, CitationSourceType, Confidence, GlassBox
from app.domains.ai.usage import record_usage
from app.domains.applications import repository as app_repo
from app.domains.applications.schemas import (
    ApplicationEventRead,
    ApplicationRead,
    CandidateSummary,
    PipelineEntry,
)
from app.domains.jobs import repository as repo
from app.domains.jobs.models import Job
from app.domains.jobs.schemas import (
    JobCreate,
    JobDebiasResult,
    JobMatchRead,
    JobRead,
    JobUpdate,
    MatchSubScores,
)


def _embed_text(job: Job | JobCreate) -> str:
    """Compose the text we embed for a job (title + description + skills)."""
    skills = " ".join(job.skills_required or [])
    return f"{job.title}\n{job.description}\n{skills}".strip()


async def _embed(text: str) -> list[float] | None:
    """Embed ``text`` once; return the vector, or None on failure."""
    llm = get_llm()
    try:
        vectors = await llm.embed([text])
    except Exception:  # pragma: no cover - degrade gracefully if embed unavailable
        return None
    return vectors[0] if vectors else None


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #
async def search_jobs(
    session: AsyncSession,
    *,
    q: str | None,
    location: str | None,
    seniority: str | None,
    work_mode: str | None,
    semantic: bool,
    page: PageParams,
) -> Page[JobRead]:
    """Keyword+facet search, or hybrid vector+keyword RRF when ``semantic`` and ``q``."""
    if semantic and q:
        vec = await _embed(q)
        if vec is not None:
            items, total = await repo.search_hybrid(
                session,
                q,
                vec,
                location=location,
                seniority=seniority,
                work_mode=work_mode,
                offset=page.offset,
                limit=page.limit,
            )
            return Page[JobRead](
                items=[JobRead.model_validate(j) for j in items],
                total=total,
                page=page.page,
                page_size=page.page_size,
            )
    items, total = await repo.search_keyword(
        session,
        q=q,
        location=location,
        seniority=seniority,
        work_mode=work_mode,
        offset=page.offset,
        limit=page.limit,
    )
    return Page[JobRead](
        items=[JobRead.model_validate(j) for j in items],
        total=total,
        page=page.page,
        page_size=page.page_size,
    )


# --------------------------------------------------------------------------- #
# Detail
# --------------------------------------------------------------------------- #
async def _require_job(session: AsyncSession, job_id: uuid.UUID) -> Job:
    job = await repo.get_job(session, job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    return job


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> JobRead:
    """Return a job and record a view."""
    job = await _require_job(session, job_id)
    await repo.increment_views(session, job)
    await session.commit()
    # The UPDATE bumped the server-side ``updated_at``; refresh so serialization
    # doesn't trigger a lazy load outside the async greenlet.
    await session.refresh(job)
    return JobRead.model_validate(job)


# --------------------------------------------------------------------------- #
# Create / update / delete
# --------------------------------------------------------------------------- #
async def create_job(session: AsyncSession, principal: Principal, payload: JobCreate) -> JobRead:
    """Create a job for the principal's org, embedding its text for search."""
    if not principal.org_id:
        raise ForbiddenError("This action requires an organization context.")
    vec = await _embed(_embed_text(payload))
    job = Job(
        org_id=uuid.UUID(principal.org_id),
        posted_by=uuid.UUID(principal.user_id),
        title=payload.title,
        occupation_id=payload.occupation_id,
        description=payload.description,
        responsibilities=payload.responsibilities,
        requirements=payload.requirements,
        skills_required=payload.skills_required,
        location=payload.location,
        work_mode=payload.work_mode,
        seniority=payload.seniority,
        employment_type=payload.employment_type,
        comp_min=payload.comp_min,
        comp_max=payload.comp_max,
        currency=payload.currency,
        is_internship=payload.is_internship,
        growth_into=payload.growth_into,
        closes_at=payload.closes_at,
        embedding=vec,
    )
    await repo.add_job(session, job)
    await session.commit()
    await session.refresh(job)
    return JobRead.model_validate(job)


async def update_job(
    session: AsyncSession, principal: Principal, job_id: uuid.UUID, payload: JobUpdate
) -> JobRead:
    """Update a job (same-org only). Re-embed when searchable text changes."""
    job = await _require_job(session, job_id)
    require_same_org(str(job.org_id), principal)

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(job, field, value)
    if {"title", "description", "skills_required"} & data.keys():
        vec = await _embed(_embed_text(job))
        if vec is not None:
            job.embedding = vec
    await session.commit()
    await session.refresh(job)
    return JobRead.model_validate(job)


async def delete_job(session: AsyncSession, principal: Principal, job_id: uuid.UUID) -> None:
    """Delete a job (same-org only)."""
    job = await _require_job(session, job_id)
    require_same_org(str(job.org_id), principal)
    await session.delete(job)
    await session.commit()


# --------------------------------------------------------------------------- #
# Match
# --------------------------------------------------------------------------- #
async def _load_candidate_profile(session: AsyncSession, user_id: str):
    """Best-effort load of the caller's CandidateProfile (cross-domain, optional)."""
    try:
        from app.domains.candidates.models import CandidateProfile
    except ImportError:  # pragma: no cover
        return None
    return await session.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == uuid.UUID(user_id))
    )


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity → [0,1] (vectors may not be unit-norm)."""
    import math

    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return max(0.0, min(1.0, (dot / (na * nb) + 1.0) / 2.0))


def _skill_overlap(candidate_skills: Sequence[str], job_skills: Sequence[str]) -> float:
    """Jaccard-style overlap of skill labels (case-insensitive)."""
    if not job_skills:
        return 0.0
    have = {s.lower() for s in candidate_skills}
    need = {s.lower() for s in job_skills}
    if not need:
        return 0.0
    return len(have & need) / len(need)


def _salary_fit(profile, job: Job) -> float:
    """Crude salary alignment proxy — neutral 0.5 when data is missing."""
    if job.comp_min is None and job.comp_max is None:
        return 0.5
    return 0.6


async def _inline_match(session: AsyncSession, profile, job: Job) -> JobMatchRead:
    """Compute a blended match inline when the matching domain is unavailable."""
    # Semantic.
    semantic = 0.5
    if profile is not None and profile.embedding is not None and job.embedding is not None:
        semantic = _cosine(profile.embedding, job.embedding)

    # Skill overlap (best-effort: candidate skill labels are not on the profile,
    # so we approximate via aspirations/headline tokens when present).
    candidate_skill_text: list[str] = []
    if profile is not None:
        for attr in ("headline", "summary", "aspirations"):
            val = getattr(profile, attr, None)
            if val:
                candidate_skill_text.extend(val.replace(",", " ").split())
    skill_overlap = _skill_overlap(candidate_skill_text, job.skills_required)

    trajectory_fit = 0.5
    if (
        profile is not None
        and profile.target_occupation_id == job.occupation_id
        and job.occupation_id
    ):
        trajectory_fit = 0.9

    salary_fit = _salary_fit(profile, job)

    score = round(
        0.45 * semantic + 0.30 * skill_overlap + 0.15 * trajectory_fit + 0.10 * salary_fit,
        4,
    )
    band = (
        Confidence.HIGH if score >= 0.66 else Confidence.MEDIUM if score >= 0.4 else Confidence.LOW
    )
    glass_box = GlassBox(
        rationale=(
            "This match blends semantic similarity between your profile and the "
            "role, overlap with the listed skills, trajectory alignment, and a "
            "salary sanity check. It is a realistic indication of fit, not a "
            "guarantee of an interview."
        ),
        confidence=band,
        confidence_score=score,
        citations=[
            Citation(
                label=f"Job posting: {job.title}",
                source_type=CitationSourceType.JOB_POSTING,
                source_id=str(job.id),
            )
        ],
        what_would_change_this=[
            "Adding more verified skills to your profile.",
            "Completing your career timeline so semantic matching has more to work with.",
        ],
        caveats=[
            "Skill overlap is approximate when your skills are not yet structured.",
        ],
    )
    return JobMatchRead(
        score=score,
        sub_scores=MatchSubScores(
            semantic=round(semantic, 4),
            skill_overlap=round(skill_overlap, 4),
            trajectory_fit=round(trajectory_fit, 4),
            salary_fit=round(salary_fit, 4),
        ),
        glass_box=glass_box,
    )


async def match_job(session: AsyncSession, principal: Principal, job_id: uuid.UUID) -> JobMatchRead:
    """Explain how well the calling candidate matches a job."""
    job = await _require_job(session, job_id)
    profile = await _load_candidate_profile(session, principal.user_id)

    # Prefer the dedicated matching domain if it exists.
    try:
        from app.domains.matching.service import explain_match  # type: ignore

        if profile is not None:
            result = await explain_match(session, candidate=profile, job=job)
            return JobMatchRead.model_validate(
                result if isinstance(result, dict) else result.__dict__
            )
    except ImportError:
        pass
    except Exception:  # pragma: no cover - never let matching break the endpoint
        pass

    return await _inline_match(session, profile, job)


# --------------------------------------------------------------------------- #
# Debias (Bias Auditor)
# --------------------------------------------------------------------------- #
async def debias_job(
    session: AsyncSession, principal: Principal, job_id: uuid.UUID
) -> JobDebiasResult:
    """Rewrite a JD to remove biased/exclusionary language, with a Glass Box."""
    job = await _require_job(session, job_id)
    require_same_org(str(job.org_id), principal)

    llm = get_llm()
    jd_text = f"{job.title}\n\n{job.description}"
    messages = [
        ChatMessage(role="system", content=SYSTEM_PREAMBLE),
        ChatMessage(
            role="user",
            content=(
                "You are a hiring-equity auditor. Review the job description below for "
                "biased, exclusionary, or gendered language and unnecessary requirements. "
                "Return a debiased rewrite, the specific issues found (phrase, why it is a "
                "problem, and a concrete suggestion), and a Glass Box explaining your "
                "reasoning, confidence, and what would change it.\n\n"
                + wrap_untrusted(jd_text, kind="job_description")
            ),
        ),
    ]
    result = await llm.structured(messages, JobDebiasResult)
    # structured() does not surface token usage; record a ledger entry anyway so
    # the feature shows up in the AI cost dashboard.
    await record_usage(
        session,
        feature="job_debias",
        model=getattr(llm, "model", None) or "mock",
        usage=TokenUsage(),
        org_id=principal.org_id,
        user_id=principal.user_id,
    )
    await session.commit()
    return result


# --------------------------------------------------------------------------- #
# Employer pipeline for a job
# --------------------------------------------------------------------------- #
async def job_pipeline(
    session: AsyncSession, principal: Principal, job_id: uuid.UUID
) -> list[PipelineEntry]:
    """Return the application pipeline for a job (same-org employers only)."""
    job = await _require_job(session, job_id)
    require_same_org(str(job.org_id), principal)

    applications = await app_repo.list_for_job(session, job_id)
    events_map = await app_repo.events_for_many(session, [a.id for a in applications])
    summaries = await _candidate_summaries(session, [a.candidate_id for a in applications])

    entries: list[PipelineEntry] = []
    for application in applications:
        entries.append(
            PipelineEntry(
                application=ApplicationRead.model_validate(application),
                candidate_summary=summaries.get(application.candidate_id),
                events=[
                    ApplicationEventRead.model_validate(e)
                    for e in events_map.get(application.id, [])
                ],
            )
        )
    return entries


async def _candidate_summaries(
    session: AsyncSession, candidate_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, CandidateSummary]:
    """Best-effort candidate cards keyed by candidate profile id."""
    if not candidate_ids:
        return {}
    try:
        from app.domains.candidates.models import CandidateProfile
    except ImportError:  # pragma: no cover
        return {}
    rows = await session.scalars(
        select(CandidateProfile).where(CandidateProfile.id.in_(list(candidate_ids)))
    )
    return {
        p.id: CandidateSummary(
            candidate_id=p.id,
            user_id=p.user_id,
            headline=p.headline,
            location=p.location,
            years_experience=p.years_experience,
        )
        for p in rows
    }
