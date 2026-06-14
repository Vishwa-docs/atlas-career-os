"""All DB access for the applications domain (async SQLAlchemy 2.0)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.applications.models import Application, ApplicationEvent


async def get_application(session: AsyncSession, application_id: uuid.UUID) -> Application | None:
    return await session.get(Application, application_id)


async def get_by_candidate_and_job(
    session: AsyncSession, candidate_id: uuid.UUID, job_id: uuid.UUID
) -> Application | None:
    return await session.scalar(
        select(Application).where(
            Application.candidate_id == candidate_id,
            Application.job_id == job_id,
        )
    )


async def add_application(session: AsyncSession, application: Application) -> Application:
    session.add(application)
    await session.flush()
    return application


def add_event(session: AsyncSession, event: ApplicationEvent) -> ApplicationEvent:
    session.add(event)
    return event


async def list_for_candidate(session: AsyncSession, candidate_id: uuid.UUID) -> list[Application]:
    rows = await session.scalars(
        select(Application)
        .where(Application.candidate_id == candidate_id)
        .order_by(Application.created_at.desc())
    )
    return list(rows)


async def list_for_job(session: AsyncSession, job_id: uuid.UUID) -> list[Application]:
    rows = await session.scalars(
        select(Application)
        .where(Application.job_id == job_id)
        .order_by(Application.created_at.desc())
    )
    return list(rows)


async def events_for(session: AsyncSession, application_id: uuid.UUID) -> list[ApplicationEvent]:
    rows = await session.scalars(
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application_id)
        .order_by(ApplicationEvent.created_at.asc())
    )
    return list(rows)


async def events_for_many(
    session: AsyncSession, application_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[ApplicationEvent]]:
    """Batch-load events for several applications → {application_id: [events]}."""
    out: dict[uuid.UUID, list[ApplicationEvent]] = {}
    if not application_ids:
        return out
    rows = await session.scalars(
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id.in_(list(application_ids)))
        .order_by(ApplicationEvent.created_at.asc())
    )
    for event in rows:
        out.setdefault(event.application_id, []).append(event)
    return out
