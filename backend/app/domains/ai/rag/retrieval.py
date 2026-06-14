"""Retrieval helpers that ground Atlas's prompts in real records.

Two jobs:
1. Build a compact, PII-aware *candidate context* string from their profile,
   recent career events, and recorded skills.
2. Fetch *market facts* (occupation salary anchor, realistic transitions, rising
   /cooling skills) so the model reasons over evidence, not vibes.

All cross-domain imports are read-only and wrapped so a sparse/partial schema
still degrades gracefully.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.guardrails import wrap_untrusted
from app.domains.ai.schemas import Citation, CitationSourceType


# --------------------------------------------------------------------------- #
# Candidate context
# --------------------------------------------------------------------------- #
async def build_candidate_context(
    session: AsyncSession, candidate: Any, *, max_events: int = 8, max_skills: int = 25
) -> str:
    """Render a wrapped, summarised context block for a candidate profile.

    The result is fenced with :func:`wrap_untrusted` because it contains
    user-authored free text (summary, aspirations, narratives).
    """
    lines: list[str] = []
    lines.append(f"Headline: {getattr(candidate, 'headline', None) or '(none)'}")
    lines.append(f"Location: {getattr(candidate, 'location', None) or '(unknown)'}")
    lines.append(f"Years of experience: {getattr(candidate, 'years_experience', 0.0):.1f}")
    summary = getattr(candidate, "summary", None)
    if summary:
        lines.append(f"Summary: {summary[:600]}")
    aspirations = getattr(candidate, "aspirations", None)
    if aspirations:
        lines.append(f"Aspirations: {aspirations[:400]}")

    events = await _recent_career_events(session, candidate, limit=max_events)
    if events:
        lines.append("Recent career timeline:")
        for ev in events:
            span = _format_span(ev)
            org = f" @ {ev.organization}" if getattr(ev, "organization", None) else ""
            lines.append(f"  - [{ev.type}] {ev.title}{org} {span}".rstrip())
            if getattr(ev, "skills_used", None):
                lines.append(f"      skills: {', '.join(ev.skills_used[:10])}")

    skills = await candidate_skill_lines(session, candidate, limit=max_skills)
    if skills:
        lines.append(f"Recorded skills: {', '.join(skills)}")

    if len(lines) <= 3:
        lines.append("(Profile is sparse — treat conclusions as low-confidence.)")

    return wrap_untrusted("\n".join(lines), kind="candidate_profile")


async def _recent_career_events(session: AsyncSession, candidate: Any, *, limit: int) -> list[Any]:
    try:
        from app.domains.candidates.models import CareerEvent

        stmt = (
            select(CareerEvent)
            .where(CareerEvent.candidate_id == candidate.id)
            .order_by(
                CareerEvent.is_current.desc(),
                CareerEvent.start_date.desc().nullslast(),
            )
            .limit(limit)
        )
        return list((await session.execute(stmt)).scalars().all())
    except ImportError:  # pragma: no cover - defensive
        return []
    except Exception:  # noqa: BLE001 - never break a prompt on context fetch
        return []


async def candidate_skill_lines(
    session: AsyncSession, candidate: Any, *, limit: int = 25
) -> list[str]:
    """Skill names recorded for the candidate, strongest first."""
    try:
        from app.domains.candidates.models import CandidateSkill
        from app.domains.taxonomy.models import Skill

        stmt = (
            select(Skill.name)
            .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
            .where(CandidateSkill.candidate_id == candidate.id)
            .order_by(CandidateSkill.proficiency.desc())
            .limit(limit)
        )
        return list((await session.execute(stmt)).scalars().all())
    except Exception:  # noqa: BLE001
        return []


def _format_span(event: Any) -> str:
    start = getattr(event, "start_date", None)
    end = getattr(event, "end_date", None)
    if getattr(event, "is_current", False):
        return f"({start or '?'} – present)" if start else "(current)"
    if start and end:
        return f"({start} – {end})"
    if start:
        return f"({start})"
    return ""


# --------------------------------------------------------------------------- #
# Market / taxonomy facts
# --------------------------------------------------------------------------- #
async def get_occupation(session: AsyncSession, occupation_id: uuid.UUID | None) -> Any:
    if occupation_id is None:
        return None
    try:
        from app.domains.taxonomy.models import Occupation

        return await session.get(Occupation, occupation_id)
    except Exception:  # noqa: BLE001
        return None


async def realistic_transitions(
    session: AsyncSession, from_occupation_id: uuid.UUID | None, *, limit: int = 6
) -> list[dict[str, Any]]:
    """Top empirical next-moves from an occupation, with target titles + stats."""
    if from_occupation_id is None:
        return []
    try:
        from app.domains.taxonomy.models import Occupation, OccupationTransition

        stmt = (
            select(
                OccupationTransition.to_occupation_id,
                OccupationTransition.weight,
                OccupationTransition.median_months,
                OccupationTransition.median_salary_delta_pct,
                Occupation.title,
                Occupation.median_salary_myr,
            )
            .join(Occupation, Occupation.id == OccupationTransition.to_occupation_id)
            .where(OccupationTransition.from_occupation_id == from_occupation_id)
            .order_by(OccupationTransition.weight.desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()
        return [
            {
                "to_occupation_id": str(to_id),
                "title": title,
                "weight": float(weight or 0.0),
                "median_months": months,
                "salary_delta_pct": delta,
                "median_salary_myr": median_salary,
            }
            for (to_id, weight, months, delta, title, median_salary) in rows
        ]
    except Exception:  # noqa: BLE001
        return []


async def occupation_skills(
    session: AsyncSession, occupation_id: uuid.UUID | None, *, limit: int = 20
) -> list[dict[str, Any]]:
    """Skills an occupation needs, with importance + level — to compute gaps."""
    if occupation_id is None:
        return []
    try:
        from app.domains.taxonomy.models import OccupationSkill, Skill

        stmt = (
            select(
                Skill.id,
                Skill.name,
                OccupationSkill.importance,
                OccupationSkill.level,
                Skill.demand_trend,
            )
            .join(OccupationSkill, OccupationSkill.skill_id == Skill.id)
            .where(OccupationSkill.occupation_id == occupation_id)
            .order_by(OccupationSkill.importance.desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()
        return [
            {
                "skill_id": str(skill_id),
                "skill": name,
                "importance": float(imp or 0.0),
                "level": float(lvl if lvl is not None else 0.5),
                "demand_trend": float(dt or 0.0),
            }
            for (skill_id, name, imp, lvl, dt) in rows
        ]
    except Exception:  # noqa: BLE001
        return []


async def candidate_skill_map(
    session: AsyncSession, candidate: Any
) -> dict[str, float]:
    """Map of skill_id (str) → candidate proficiency (0..1) for gap maths."""
    try:
        from app.domains.candidates.models import CandidateSkill

        stmt = select(CandidateSkill.skill_id, CandidateSkill.proficiency).where(
            CandidateSkill.candidate_id == candidate.id
        )
        rows = (await session.execute(stmt)).all()
        return {str(sid): float(prof or 0.0) for (sid, prof) in rows}
    except Exception:  # noqa: BLE001
        return {}


async def occupation_demand_trend(
    session: AsyncSession, occupation_id: uuid.UUID | None
) -> float | None:
    """Average ``Skill.demand_trend`` across an occupation's skills, or None."""
    if occupation_id is None:
        return None
    try:
        from app.domains.taxonomy.models import OccupationSkill, Skill

        stmt = (
            select(Skill.demand_trend)
            .join(OccupationSkill, OccupationSkill.skill_id == Skill.id)
            .where(OccupationSkill.occupation_id == occupation_id)
        )
        trends = [float(t or 0.0) for (t,) in (await session.execute(stmt)).all()]
        if not trends:
            return None
        return sum(trends) / len(trends)
    except Exception:  # noqa: BLE001
        return None


async def fallback_occupations(
    session: AsyncSession,
    *,
    exclude_id: uuid.UUID | None,
    family: str | None,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Sensible Atlas routes when no transitions exist.

    Prefer occupations in the same family; otherwise the highest-median roles.
    """
    try:
        from app.domains.taxonomy.models import Occupation

        base = select(Occupation.id, Occupation.title, Occupation.median_salary_myr)
        if exclude_id is not None:
            base = base.where(Occupation.id != exclude_id)
        rows: list[Any] = []
        if family:
            fam_stmt = (
                base.where(Occupation.family == family)
                .order_by(Occupation.median_salary_myr.desc().nullslast())
                .limit(limit)
            )
            rows = list((await session.execute(fam_stmt)).all())
        if len(rows) < limit:
            top_stmt = base.order_by(
                Occupation.median_salary_myr.desc().nullslast()
            ).limit(limit * 2)
            seen = {r[0] for r in rows}
            for r in (await session.execute(top_stmt)).all():
                if r[0] in seen:
                    continue
                rows.append(r)
                if len(rows) >= limit:
                    break
        return [
            {
                "to_occupation_id": str(occ_id),
                "title": title,
                "weight": 0.0,
                "median_months": None,
                "salary_delta_pct": None,
                "median_salary_myr": median_salary,
            }
            for (occ_id, title, median_salary) in rows[:limit]
        ]
    except Exception:  # noqa: BLE001
        return []


async def find_transition(
    session: AsyncSession,
    from_occupation_id: uuid.UUID | None,
    to_occupation_id: uuid.UUID,
) -> dict[str, Any] | None:
    """The single empirical transition edge from→to, if one exists."""
    if from_occupation_id is None:
        return None
    try:
        from app.domains.taxonomy.models import OccupationTransition

        stmt = select(
            OccupationTransition.weight,
            OccupationTransition.median_months,
            OccupationTransition.median_salary_delta_pct,
        ).where(
            OccupationTransition.from_occupation_id == from_occupation_id,
            OccupationTransition.to_occupation_id == to_occupation_id,
        )
        row = (await session.execute(stmt)).first()
        if row is None:
            return None
        weight, months, delta = row
        return {
            "weight": float(weight or 0.0),
            "median_months": months,
            "salary_delta_pct": delta,
        }
    except Exception:  # noqa: BLE001
        return None


async def skill_trends(
    session: AsyncSession, occupation_id: uuid.UUID | None = None, *, limit: int = 8
) -> dict[str, list[str]]:
    """Rising / cooling skills, optionally scoped to an occupation's skill set."""
    rising: list[str] = []
    cooling: list[str] = []
    try:
        from app.domains.taxonomy.models import OccupationSkill, Skill

        stmt = select(Skill.name, Skill.demand_trend)
        if occupation_id is not None:
            stmt = stmt.join(OccupationSkill, OccupationSkill.skill_id == Skill.id).where(
                OccupationSkill.occupation_id == occupation_id
            )
        rows = (await session.execute(stmt)).all()
        ranked = sorted(rows, key=lambda r: r[1] or 0.0, reverse=True)
        rising = [name for (name, dt) in ranked if (dt or 0.0) > 0][:limit]
        cooling = [name for (name, dt) in reversed(ranked) if (dt or 0.0) < 0][:limit]
    except Exception:  # noqa: BLE001
        pass
    return {"rising": rising, "cooling": cooling}


# --------------------------------------------------------------------------- #
# Citation helpers (so services produce consistent grounding labels)
# --------------------------------------------------------------------------- #
def salary_citation(occupation: Any) -> Citation:
    median = getattr(occupation, "median_salary_myr", None) if occupation else None
    title = getattr(occupation, "title", "role") if occupation else "role"
    return Citation(
        label=f"Median salary anchor for {title}",
        source_type=CitationSourceType.SALARY_DATA,
        source_id=str(getattr(occupation, "id", "")) or None,
        snippet=(f"OpenDOSM median ≈ MYR {median}/month" if median else "No median available"),
    )


def transition_citation(transitions: list[dict[str, Any]]) -> Citation:
    titles = ", ".join(t["title"] for t in transitions[:4]) or "(none observed)"
    return Citation(
        label="Realistic next moves (transition graph)",
        source_type=CitationSourceType.LABOR_MARKET,
        snippet=f"Observed transitions: {titles}",
    )
