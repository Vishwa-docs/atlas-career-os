"""Background task: re-embed profiles and jobs whose vector is stale/missing.

Embeddings power semantic matching. When a profile or job is created without an
embedding (e.g. the LLM/embedder was unavailable at write time) its ``embedding``
column is left ``NULL``. This periodic job backfills those rows in batches using
the same text-composition helpers the write paths use, so vectors stay consistent.

Opens its own :class:`AsyncSession` and commits at the boundary. Degrades
gracefully if the embedder is unavailable (leaves rows for the next run).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.core.db import SessionFactory
from app.core.logging import get_logger

log = get_logger(__name__)

# Cap rows processed per run so a backlog can't monopolise the worker.
_BATCH_LIMIT = 100


async def reembed_stale(ctx: dict[str, Any]) -> dict[str, int]:
    """Re-embed candidate profiles and jobs whose ``embedding`` is NULL.

    Selects up to ``_BATCH_LIMIT`` of each, rebuilds the embedding text via the
    domains' own composition helpers, embeds via the shared LLM client, and
    writes the vectors back. Returns ``{profiles, jobs}`` counts re-embedded.
    """
    from app.domains.ai.llm.factory import get_llm
    from app.domains.candidates.models import CandidateProfile

    # Reuse the exact text-composition the write paths use, so vectors match.
    from app.domains.candidates.service import build_profile_text
    from app.domains.jobs.models import Job
    from app.domains.jobs.service import _embed_text as build_job_text

    llm = get_llm()
    profiles_done = 0
    jobs_done = 0

    async with SessionFactory() as session:
        # --- candidate profiles ---
        profiles = list(
            await session.scalars(
                select(CandidateProfile)
                .where(CandidateProfile.embedding.is_(None))
                .limit(_BATCH_LIMIT)
            )
        )
        for profile in profiles:
            skill_names = await _profile_skill_names(session, profile.id)
            text = build_profile_text(profile, skill_names)
            vec = await _embed_one(llm, text)
            if vec is not None:
                profile.embedding = vec
                profiles_done += 1

        # --- jobs ---
        jobs = list(
            await session.scalars(select(Job).where(Job.embedding.is_(None)).limit(_BATCH_LIMIT))
        )
        for job in jobs:
            vec = await _embed_one(llm, build_job_text(job))
            if vec is not None:
                job.embedding = vec
                jobs_done += 1

        await session.commit()

    log.info("workers.embeddings.reembedded", profiles=profiles_done, jobs=jobs_done)
    return {"profiles": profiles_done, "jobs": jobs_done}


async def _profile_skill_names(session: Any, profile_id: Any) -> list[str]:
    """Resolve a profile's skill display names for embedding text."""
    from app.domains.candidates.models import CandidateSkill
    from app.domains.taxonomy.models import Skill

    rows = (
        await session.execute(
            select(Skill.name)
            .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
            .where(CandidateSkill.candidate_id == profile_id)
        )
    ).all()
    return [name for (name,) in rows]


async def _embed_one(llm: Any, text: str) -> list[float] | None:
    """Embed a single string; return the vector or ``None`` on failure/empty."""
    if not text or not text.strip():
        return None
    try:
        vectors = await llm.embed([text])
    except Exception:  # pragma: no cover - degrade gracefully if embed unavailable
        return None
    return vectors[0] if vectors else None
