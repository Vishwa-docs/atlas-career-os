"""Business logic for the taxonomy domain.

Read-only: composes repository queries and maps ORM rows to read schemas. Raises
:class:`NotFoundError` for missing occupations. No commits are needed (no writes).
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.schemas import Page
from app.domains.taxonomy import repository as repo
from app.domains.taxonomy.schemas import (
    OccupationDetail,
    OccupationRead,
    OccupationSkillRead,
    OccupationTransitionEdge,
    SkillRead,
)


async def list_skills(
    session: AsyncSession,
    *,
    q: str | None,
    category: str | None,
    page: int,
    page_size: int,
    offset: int,
) -> Page[SkillRead]:
    """Paginate skills, optionally filtered by name fragment and category."""
    total = await repo.count_skills(session, q=q, category=category)
    rows = await repo.list_skills(session, q=q, category=category, offset=offset, limit=page_size)
    return Page[SkillRead](
        items=[SkillRead.model_validate(s) for s in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def list_occupations(
    session: AsyncSession,
    *,
    q: str | None,
    family: str | None,
    page: int,
    page_size: int,
    offset: int,
) -> Page[OccupationRead]:
    """Paginate occupations, optionally filtered by title fragment and family."""
    total = await repo.count_occupations(session, q=q, family=family)
    rows = await repo.list_occupations(session, q=q, family=family, offset=offset, limit=page_size)
    return Page[OccupationRead](
        items=[OccupationRead.model_validate(o) for o in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_occupation_detail(
    session: AsyncSession, occupation_id: uuid.UUID
) -> OccupationDetail:
    """Return an occupation with its skill requirements and salary anchor."""
    occupation = await repo.get_occupation(session, occupation_id)
    if occupation is None:
        raise NotFoundError("Occupation not found.")

    skill_rows = await repo.list_occupation_skills(session, occupation_id)
    skills = [
        OccupationSkillRead(
            skill=SkillRead.model_validate(skill),
            importance=link.importance,
            level=link.level,
            essential=link.essential,
        )
        for link, skill in skill_rows
    ]
    return OccupationDetail(
        occupation=OccupationRead.model_validate(occupation),
        skills=skills,
        median_salary_myr=occupation.median_salary_myr,
    )


async def list_transitions(
    session: AsyncSession, occupation_id: uuid.UUID
) -> list[OccupationTransitionEdge]:
    """Return the "realistic next moves" out of an occupation, weight desc."""
    occupation = await repo.get_occupation(session, occupation_id)
    if occupation is None:
        raise NotFoundError("Occupation not found.")

    rows = await repo.list_transitions(session, occupation_id)
    return [
        OccupationTransitionEdge(
            to_occupation=OccupationRead.model_validate(to_occ),
            weight=edge.weight,
            median_months=edge.median_months,
            median_salary_delta_pct=edge.median_salary_delta_pct,
        )
        for edge, to_occ in rows
    ]
