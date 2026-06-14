"""All DB access for the jobs domain (async SQLAlchemy 2.0).

Search supports two modes: a plain keyword+filter query, and a hybrid
vector+keyword query fused with Reciprocal Rank Fusion (RRF). Keeping the ranking
maths here keeps the service thin.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.jobs.models import Job

# RRF damping constant — the standard k=60 from the original paper.
_RRF_K = 60


def _apply_filters(
    stmt: Select,
    *,
    q: str | None,
    location: str | None,
    seniority: str | None,
    work_mode: str | None,
) -> Select:
    """Apply the shared status/keyword/facet filters to a Job select."""
    stmt = stmt.where(Job.status == "open")
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Job.title.ilike(like), Job.description.ilike(like)))
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location}%"))
    if seniority:
        stmt = stmt.where(Job.seniority == seniority)
    if work_mode:
        stmt = stmt.where(Job.work_mode == work_mode)
    return stmt


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    return await session.get(Job, job_id)


async def add_job(session: AsyncSession, job: Job) -> Job:
    session.add(job)
    await session.flush()
    return job


async def increment_views(session: AsyncSession, job: Job) -> None:
    job.views = (job.views or 0) + 1


async def search_keyword(
    session: AsyncSession,
    *,
    q: str | None,
    location: str | None,
    seniority: str | None,
    work_mode: str | None,
    offset: int,
    limit: int,
) -> tuple[list[Job], int]:
    """Plain keyword + facet search, newest first, with total count."""
    base = _apply_filters(
        select(Job), q=q, location=location, seniority=seniority, work_mode=work_mode
    )
    total = await session.scalar(select(func.count()).select_from(base.order_by(None).subquery()))
    rows = await session.scalars(base.order_by(Job.created_at.desc()).offset(offset).limit(limit))
    return list(rows), int(total or 0)


async def _ranked_ids_semantic(
    session: AsyncSession,
    vec: Sequence[float],
    *,
    location: str | None,
    seniority: str | None,
    work_mode: str | None,
    pool: int,
) -> list[uuid.UUID]:
    """Job ids ranked by ascending vector cosine distance (best first)."""
    stmt = _apply_filters(
        select(Job.id), q=None, location=location, seniority=seniority, work_mode=work_mode
    ).where(Job.embedding.is_not(None))
    stmt = stmt.order_by(Job.embedding.cosine_distance(vec)).limit(pool)
    rows = await session.scalars(stmt)
    return list(rows)


async def _ranked_ids_keyword(
    session: AsyncSession,
    q: str,
    *,
    location: str | None,
    seniority: str | None,
    work_mode: str | None,
    pool: int,
) -> list[uuid.UUID]:
    """Job ids ranked by full-text relevance (ts_rank), best first.

    Falls back gracefully: results are bounded by the keyword filter already
    applied, so even a thin tsvector match keeps recall reasonable.
    """
    tsv = func.to_tsvector("english", func.concat(Job.title, " ", Job.description))
    tsq = func.websearch_to_tsquery("english", q)
    rank = func.ts_rank(tsv, tsq)
    stmt = _apply_filters(
        select(Job.id, rank.label("rank")),
        q=q,
        location=location,
        seniority=seniority,
        work_mode=work_mode,
    )
    stmt = stmt.order_by(rank.desc(), Job.created_at.desc()).limit(pool)
    rows = await session.execute(stmt)
    return [row[0] for row in rows]


def reciprocal_rank_fusion(*ranked_lists: list[uuid.UUID]) -> list[uuid.UUID]:
    """Fuse several ranked id-lists into one via RRF (score = Σ 1/(k+rank))."""
    scores: dict[uuid.UUID, float] = {}
    for ranked in ranked_lists:
        for rank, _id in enumerate(ranked):
            scores[_id] = scores.get(_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
    return sorted(scores, key=lambda _id: scores[_id], reverse=True)


async def fetch_jobs_by_ids(
    session: AsyncSession, ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, Job]:
    """Load jobs for the given ids; return a id→Job map (order-agnostic)."""
    if not ids:
        return {}
    rows = await session.scalars(select(Job).where(Job.id.in_(list(ids))))
    return {job.id: job for job in rows}


async def search_hybrid(
    session: AsyncSession,
    q: str,
    vec: Sequence[float],
    *,
    location: str | None,
    seniority: str | None,
    work_mode: str | None,
    offset: int,
    limit: int,
) -> tuple[list[Job], int]:
    """Hybrid search: fuse vector + keyword rankings with RRF, then paginate."""
    pool = max(offset + limit, 50)
    semantic_ids = await _ranked_ids_semantic(
        session, vec, location=location, seniority=seniority, work_mode=work_mode, pool=pool
    )
    keyword_ids = await _ranked_ids_keyword(
        session, q, location=location, seniority=seniority, work_mode=work_mode, pool=pool
    )
    fused = reciprocal_rank_fusion(semantic_ids, keyword_ids)
    total = len(fused)
    page_ids = fused[offset : offset + limit]
    by_id = await fetch_jobs_by_ids(session, page_ids)
    items = [by_id[i] for i in page_ids if i in by_id]
    return items, total


async def list_jobs_for_org(session: AsyncSession, org_id: uuid.UUID) -> list[Job]:
    rows = await session.scalars(
        select(Job).where(Job.org_id == org_id).order_by(Job.created_at.desc())
    )
    return list(rows)
