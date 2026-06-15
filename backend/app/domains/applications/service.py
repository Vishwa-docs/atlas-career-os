"""Business logic for applications: apply, list, advance through the pipeline.

Owns authorization (a candidate acts only on their own applications; an employer
acts only within the org that owns the job), the status state-machine, the event
timeline, and best-effort candidate notifications.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, require_same_org
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domains.applications import repository as repo
from app.domains.applications.models import Application, ApplicationEvent
from app.domains.applications.schemas import (
    VALID_STATUSES,
    ApplicationCreate,
    ApplicationEventFlat,
    ApplicationRead,
    ApplicationStatusUpdate,
    CandidateApplicationRow,
)


# --------------------------------------------------------------------------- #
# Cross-domain helpers (kept optional so the domain degrades gracefully).
# --------------------------------------------------------------------------- #
async def _candidate_profile_for_user(session: AsyncSession, user_id: str):
    """Resolve the calling candidate's profile, or raise if there is none."""
    try:
        from app.domains.candidates.models import CandidateProfile
    except ImportError as exc:  # pragma: no cover
        raise NotFoundError("Candidate profile not found.") from exc
    profile = await session.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == uuid.UUID(user_id))
    )
    if profile is None:
        raise NotFoundError("Create a candidate profile before applying.")
    return profile


async def _get_job(session: AsyncSession, job_id: uuid.UUID):
    """Load a job via the jobs repository (raise NotFound if missing)."""
    from app.domains.jobs import repository as jobs_repo

    job = await jobs_repo.get_job(session, job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    return job


async def _notify(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    type_: str,
    title: str,
    body: str | None,
    link: str | None,
) -> None:
    """Best-effort in-app notification; never let it break the flow."""
    try:
        from app.domains.notifications.service import create_notification  # type: ignore
    except ImportError:
        return
    try:
        await create_notification(
            session,
            user_id=user_id,
            type=type_,
            title=title,
            body=body,
            link=link,
        )
    except Exception:  # pragma: no cover - notifications are non-critical
        pass


async def _org_names(session: AsyncSession, org_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Map org id → name (best-effort, one batched query)."""
    if not org_ids:
        return {}
    from app.domains.organizations.models import Organization

    rows = await session.execute(
        select(Organization.id, Organization.name).where(Organization.id.in_(org_ids))
    )
    return dict(rows.all())


async def _candidate_names(
    session: AsyncSession, candidate_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """Map candidate-profile id → owner's full name (best-effort, one query)."""
    if not candidate_ids:
        return {}
    try:
        from app.domains.candidates.models import CandidateProfile
        from app.domains.users.models import User
    except ImportError:  # pragma: no cover
        return {}
    rows = await session.execute(
        select(CandidateProfile.id, User.full_name)
        .join(User, User.id == CandidateProfile.user_id)
        .where(CandidateProfile.id.in_(candidate_ids))
    )
    return {cid: name for cid, name in rows.all() if name}


# --------------------------------------------------------------------------- #
# Apply
# --------------------------------------------------------------------------- #
async def apply(
    session: AsyncSession, principal: Principal, payload: ApplicationCreate
) -> ApplicationRead:
    """Candidate applies to a job; idempotency enforced by unique (candidate, job)."""
    profile = await _candidate_profile_for_user(session, principal.user_id)
    job = await _get_job(session, payload.job_id)

    existing = await repo.get_by_candidate_and_job(session, profile.id, job.id)
    if existing is not None:
        raise ConflictError("You have already applied to this job.")

    application = Application(
        candidate_id=profile.id,
        job_id=job.id,
        status="applied",
        cover_note=payload.cover_note,
        source="atlas",
    )
    await repo.add_application(session, application)
    repo.add_event(
        session,
        ApplicationEvent(
            application_id=application.id,
            from_status=None,
            to_status="applied",
            actor_id=uuid.UUID(principal.user_id),
        ),
    )

    # Notify the recruiter who posted the role (if any).
    if job.posted_by is not None:
        await _notify(
            session,
            user_id=job.posted_by,
            type_="application",
            title="New application received",
            body=f"A candidate applied to {job.title}.",
            link=f"/jobs/{job.id}/applications",
        )

    await session.commit()
    await session.refresh(application)
    return ApplicationRead.model_validate(application)


# --------------------------------------------------------------------------- #
# Candidate's own applications
# --------------------------------------------------------------------------- #
async def list_my_applications(
    session: AsyncSession, principal: Principal
) -> list[CandidateApplicationRow]:
    """List the calling candidate's applications as flat cards (job + timeline)."""
    profile = await _candidate_profile_for_user(session, principal.user_id)
    applications = await repo.list_for_candidate(session, profile.id)
    events_map = await repo.events_for_many(session, [a.id for a in applications])

    from app.domains.jobs import repository as jobs_repo

    jobs_map = await jobs_repo.fetch_jobs_by_ids(session, [a.job_id for a in applications])
    org_names = await _org_names(
        session, [j.org_id for j in jobs_map.values()]
    )

    rows: list[CandidateApplicationRow] = []
    for application in applications:
        job = jobs_map.get(application.job_id)
        org_name = org_names.get(job.org_id) if job is not None else None
        timeline = [
            ApplicationEventFlat(status=e.to_status, at=e.created_at, note=e.note)
            for e in events_map.get(application.id, [])
        ]
        rows.append(
            CandidateApplicationRow(
                id=application.id,
                job_id=application.job_id,
                job_title=job.title if job is not None else "Role",
                company=org_name,
                org_name=org_name,
                location=job.location if job is not None else None,
                status=application.status,
                created_at=application.created_at,
                timeline=timeline,
            )
        )
    return rows


# --------------------------------------------------------------------------- #
# Employer advances an application
# --------------------------------------------------------------------------- #
async def update_status(
    session: AsyncSession,
    principal: Principal,
    application_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
) -> ApplicationRead:
    """Advance an application's status (employer, same org as the job)."""
    if payload.status not in VALID_STATUSES:
        raise ValidationError(
            f"Invalid status '{payload.status}'.",
            details={"allowed": sorted(VALID_STATUSES)},
        )

    application = await repo.get_application(session, application_id)
    if application is None:
        raise NotFoundError("Application not found.")

    job = await _get_job(session, application.job_id)
    require_same_org(str(job.org_id), principal)

    previous = application.status
    application.status = payload.status
    if payload.feedback is not None:
        application.feedback = payload.feedback

    repo.add_event(
        session,
        ApplicationEvent(
            application_id=application.id,
            from_status=previous,
            to_status=payload.status,
            note=payload.note,
            actor_id=uuid.UUID(principal.user_id),
        ),
    )

    # Close the loop for the candidate.
    candidate_user_id = await _candidate_user_id(session, application.candidate_id)
    if candidate_user_id is not None:
        await _notify(
            session,
            user_id=candidate_user_id,
            type_="application",
            title=f"Your application is now: {payload.status}",
            body=payload.feedback or payload.note,
            link="/applications",
        )

    await session.commit()
    await session.refresh(application)
    return ApplicationRead.model_validate(application)


async def _candidate_user_id(session: AsyncSession, candidate_id: uuid.UUID) -> uuid.UUID | None:
    """Map a candidate profile id → its owning user id (best-effort)."""
    try:
        from app.domains.candidates.models import CandidateProfile
    except ImportError:  # pragma: no cover
        return None
    profile = await session.get(CandidateProfile, candidate_id)
    return profile.user_id if profile is not None else None
