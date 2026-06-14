"""Business logic for explainable candidate↔job matching.

The scoring is fully transparent: four component sub-scores (semantic,
skill-overlap, trajectory-fit, salary-fit) are blended into a single 0..1 score,
then an LLM is asked to fill a :class:`GlassBox` *grounded in those numbers* — it
explains, it does not invent the score. Results are cached into ``MatchResult``.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.guardrails import SYSTEM_PREAMBLE, wrap_untrusted
from app.domains.ai.llm.client import ChatMessage, LLMClient
from app.domains.ai.schemas import (
    Citation,
    CitationSourceType,
    Confidence,
    GlassBox,
)
from app.domains.ai.usage import record_usage
from app.domains.candidates.models import CandidateProfile
from app.domains.jobs.models import Job
from app.domains.matching.repository import MatchingRepository
from app.domains.matching.schemas import MatchExplanation

# Weighted blend of the four transparent components → overall score.
WEIGHTS = {
    "semantic": 0.30,
    "skill_overlap": 0.30,
    "trajectory_fit": 0.20,
    "salary_fit": 0.20,
}


# --------------------------------------------------------------------------- #
# Component scorers (pure, deterministic, explainable)
# --------------------------------------------------------------------------- #
def cosine(a: Sequence[float] | None, b: Sequence[float] | None) -> float | None:
    """Cosine similarity mapped to 0..1, or ``None`` if either vector is absent."""
    # Note: pgvector returns numpy arrays — use explicit None checks, not truthiness.
    if a is None or b is None or len(a) != len(b):
        return None
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return None
    sim = dot / (na * nb)
    return max(0.0, min(1.0, (sim + 1.0) / 2.0))


def weighted_jaccard(have: Sequence[str], need: Sequence[str]) -> float:
    """Overlap of candidate skills vs required skills (case-insensitive)."""
    need_set = {s.strip().lower() for s in need if s and s.strip()}
    if not need_set:
        return 0.5  # No stated requirements → neutral.
    have_set = {s.strip().lower() for s in have if s and s.strip()}
    matched = need_set & have_set
    # Reward coverage of the *requirements* most strongly; union dampens it.
    coverage = len(matched) / len(need_set)
    union = need_set | have_set
    jaccard = len(matched) / len(union) if union else 0.0
    return max(0.0, min(1.0, 0.7 * coverage + 0.3 * jaccard))


def salary_fit(job: Job, candidate: CandidateProfile, market_median: int | None) -> float:
    """How well the job comp sits relative to the candidate's market anchor.

    Without a personal salary signal we anchor on the candidate's market median
    (their current/target occupation). Comp at-or-above market scores high;
    comp well below scores lower. Missing data → neutral 0.5.
    """
    comp = None
    if job.comp_min is not None and job.comp_max is not None:
        comp = (job.comp_min + job.comp_max) / 2.0
    elif job.comp_max is not None:
        comp = float(job.comp_max)
    elif job.comp_min is not None:
        comp = float(job.comp_min)
    if comp is None or not market_median:
        return 0.5
    ratio = comp / float(market_median)
    # 1.0 at/above market; degrade as comp falls below; clamp 0..1.
    if ratio >= 1.0:
        return min(1.0, 0.85 + 0.15 * min(ratio - 1.0, 1.0))
    return max(0.0, min(1.0, ratio * 0.85))


async def trajectory_fit(repo: MatchingRepository, candidate: CandidateProfile, job: Job) -> float:
    """Does this job move the candidate toward where they want to go?

    Prefers the empirical :class:`OccupationTransition` weight from the
    candidate's current occupation to the job's occupation; falls back to
    aspiration/growth-into heuristics.
    """
    # Strong signal: the job's occupation IS the candidate's target.
    if (
        candidate.target_occupation_id is not None
        and job.occupation_id is not None
        and candidate.target_occupation_id == job.occupation_id
    ):
        return 0.95

    # Empirical transition graph from current → job occupation.
    if candidate.current_occupation_id is not None and job.occupation_id is not None:
        tr = await repo.transition_weight(candidate.current_occupation_id, job.occupation_id)
        if tr is not None and tr.weight > 0:
            # weight is a normalized frequency; map to a confidence-ish band.
            return max(0.4, min(1.0, 0.5 + 0.5 * min(tr.weight, 1.0)))

    # Heuristic: does the job's growth_into mention the candidate's aspirations?
    aspirations = (candidate.aspirations or "").lower()
    if aspirations and job.growth_into:
        for target in job.growth_into:
            if target and target.lower() in aspirations:
                return 0.75
    # Lateral move (no clear direction) → mildly positive.
    return 0.5


# --------------------------------------------------------------------------- #
# The public matching entrypoint
# --------------------------------------------------------------------------- #
async def explain_match(
    session: AsyncSession,
    candidate: CandidateProfile,
    job: Job,
    llm: LLMClient,
    *,
    repo: MatchingRepository | None = None,
    persist: bool = True,
    actor_org_id: str | None = None,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    """Compute the transparent sub-scores, blend them, and ground a Glass Box.

    Returns ``{score, sub_scores:{...}, glass_box}``. Caches into ``MatchResult``
    (upsert) when ``persist`` is set. Robust to sparse profiles.
    """
    repo = repo or MatchingRepository(session)

    # --- semantic ---
    sem = cosine(getattr(candidate, "embedding", None), getattr(job, "embedding", None))
    semantic = 0.5 if sem is None else sem

    # --- skill overlap ---
    have_skills = await repo.candidate_skill_names(candidate.id)
    skill_overlap = weighted_jaccard(have_skills, job.skills_required or [])

    # --- trajectory ---
    traj = await trajectory_fit(repo, candidate, job)

    # --- salary ---
    market_median = await _market_median(session, candidate)
    sal = salary_fit(job, candidate, market_median)

    sub_scores = {
        "semantic": round(semantic, 4),
        "skill_overlap": round(skill_overlap, 4),
        "trajectory_fit": round(traj, 4),
        "salary_fit": round(sal, 4),
    }
    score = round(
        sum(sub_scores[k] * WEIGHTS[k] for k in WEIGHTS),
        4,
    )

    glass_box = await _build_glass_box(
        session=session,
        llm=llm,
        candidate=candidate,
        job=job,
        have_skills=have_skills,
        sub_scores=sub_scores,
        score=score,
        market_median=market_median,
        actor_org_id=actor_org_id,
        actor_user_id=actor_user_id,
    )

    if persist:
        await repo.upsert_match(
            candidate_id=candidate.id,
            job_id=job.id,
            score=score,
            sub_scores=sub_scores,
            glass_box=glass_box.model_dump(mode="json"),
        )
        await session.commit()

    return {"score": score, "sub_scores": sub_scores, "glass_box": glass_box}


async def _market_median(session: AsyncSession, candidate: CandidateProfile) -> int | None:
    """Median monthly salary anchor for the candidate's target/current role."""
    occ_id = candidate.target_occupation_id or candidate.current_occupation_id
    if occ_id is None:
        return None
    try:
        from app.domains.taxonomy.models import Occupation

        occ = await session.get(Occupation, occ_id)
        return getattr(occ, "median_salary_myr", None) if occ else None
    except ImportError:  # pragma: no cover - defensive
        return None


def _heuristic_glass_box(
    *, sub_scores: dict[str, float], score: float, job: Job, have_skills: list[str]
) -> GlassBox:
    """A deterministic, honest Glass Box used as a grounded fallback."""
    band = (
        Confidence.HIGH if score >= 0.7 else Confidence.MEDIUM if score >= 0.45 else Confidence.LOW
    )
    strongest = max(sub_scores, key=sub_scores.get)
    weakest = min(sub_scores, key=sub_scores.get)
    rationale = (
        f"Overall fit is {score:.0%}. The strongest component is "
        f"{strongest.replace('_', ' ')} ({sub_scores[strongest]:.0%}); the "
        f"weakest is {weakest.replace('_', ' ')} ({sub_scores[weakest]:.0%}). "
        "This is a realistic estimate from the candidate's graph and the posting, "
        "not a prediction of hiring outcome."
    )
    return GlassBox(
        rationale=rationale,
        confidence=band,
        confidence_score=round(min(0.9, max(0.2, score)), 2),
        citations=[
            Citation(
                label="Required skills on the job posting",
                source_type=CitationSourceType.JOB_POSTING,
                source_id=str(job.id),
                snippet=", ".join((job.skills_required or [])[:8]) or "(none listed)",
            ),
            Citation(
                label="Candidate's recorded skills",
                source_type=CitationSourceType.SKILL_TAXONOMY,
                snippet=", ".join(have_skills[:8]) or "(none recorded)",
            ),
        ],
        what_would_change_this=[
            "More verified skills matching the requirements would raise the fit.",
            "A confirmed salary expectation would sharpen the salary-fit component.",
        ],
        caveats=[
            "Sub-scores use available profile data; gaps default to neutral.",
        ],
    )


async def _build_glass_box(
    *,
    session: AsyncSession,
    llm: LLMClient,
    candidate: CandidateProfile,
    job: Job,
    have_skills: list[str],
    sub_scores: dict[str, float],
    score: float,
    market_median: int | None,
    actor_org_id: str | None,
    actor_user_id: str | None,
) -> GlassBox:
    """Ask the LLM to explain the *already-computed* numbers; fall back safely."""
    fallback = _heuristic_glass_box(
        sub_scores=sub_scores, score=score, job=job, have_skills=have_skills
    )
    context = (
        f"Overall match score (fixed, do not change): {score:.3f}\n"
        f"Sub-scores: semantic={sub_scores['semantic']:.3f}, "
        f"skill_overlap={sub_scores['skill_overlap']:.3f}, "
        f"trajectory_fit={sub_scores['trajectory_fit']:.3f}, "
        f"salary_fit={sub_scores['salary_fit']:.3f}\n"
        f"Market median salary anchor (MYR/month): {market_median or 'unknown'}\n"
        f"Candidate skills: {', '.join(have_skills[:20]) or '(none recorded)'}\n"
        f"Candidate aspirations: {candidate.aspirations or '(none stated)'}\n"
    )
    job_text = wrap_untrusted(
        f"Title: {job.title}\nSeniority: {job.seniority}\n"
        f"Required skills: {', '.join(job.skills_required or [])}\n"
        f"Description: {(job.description or '')[:1200]}",
        kind="job_posting",
    )
    messages = [
        ChatMessage(role="system", content=SYSTEM_PREAMBLE),
        ChatMessage(
            role="user",
            content=(
                "Explain this candidate↔job match for both parties. The score and "
                "sub-scores are already computed and must NOT be changed — only "
                "explain them honestly. Cite career_history, job_posting, and "
                "skill_taxonomy. Use a confidence band consistent with the score, "
                "state what would change it, and note caveats.\n\n"
                f"{context}\n{job_text}"
            ),
        ),
    ]
    try:
        result = await llm.structured(messages, MatchExplanation)
        glass_box = result.glass_box
    except Exception:  # noqa: BLE001 - never fail a match on explanation issues
        return fallback

    # Best-effort usage accounting (structured() may not expose usage).
    try:
        usage = getattr(result, "usage", None)
        if usage is not None:
            await record_usage(
                session,
                feature="matching.explain",
                model="mock-or-azure",
                usage=usage,
                org_id=actor_org_id,
                user_id=actor_user_id,
            )
    except Exception:  # noqa: BLE001
        pass

    return glass_box


# --------------------------------------------------------------------------- #
# Orchestration used by the router (candidate-side & employer-side)
# --------------------------------------------------------------------------- #
async def top_job_matches(
    session: AsyncSession,
    *,
    candidate: CandidateProfile,
    llm: LLMClient,
    limit: int,
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    """Rank open jobs for a candidate and explain the top ``limit``."""
    repo = MatchingRepository(session)
    jobs = await repo.open_jobs(limit=200)
    explained: list[dict[str, Any]] = []
    for job in jobs:
        result = await explain_match(
            session,
            candidate,
            job,
            llm,
            repo=repo,
            persist=True,
            actor_user_id=user_id,
        )
        result["job"] = job
        explained.append(result)
    explained.sort(key=lambda r: r["score"], reverse=True)
    return explained[: max(1, limit)]


async def candidates_for_job(
    session: AsyncSession,
    *,
    job: Job,
    org_id: uuid.UUID,
    query: str | None,
    llm: LLMClient,
    limit: int,
    user_id: str | None = None,
) -> list[tuple[CandidateProfile, bool, dict[str, Any]]]:
    """Consent-gated candidate matches for an employer's job.

    Returns ``(candidate, has_consent_grant, match_result)`` tuples, ranked.
    """
    repo = MatchingRepository(session)
    visible = await repo.visible_candidates_for_org(
        org_id, query=query, limit=max(limit * 3, limit)
    )
    out: list[tuple[CandidateProfile, bool, dict[str, Any]]] = []
    for candidate, has_grant in visible:
        result = await explain_match(
            session,
            candidate,
            job,
            llm,
            repo=repo,
            persist=True,
            actor_org_id=str(org_id),
            actor_user_id=user_id,
        )
        out.append((candidate, has_grant, result))
    out.sort(key=lambda t: t[2]["score"], reverse=True)
    return out[: max(1, limit)]
