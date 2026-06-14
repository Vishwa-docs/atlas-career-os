"""All database access for the taxonomy domain.

Async SQLAlchemy 2.0 ``select()`` queries only — no business logic, no HTTP. The
service layer composes these and maps rows to schemas.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.taxonomy.models import (
    Occupation,
    OccupationSkill,
    OccupationTransition,
    Skill,
)


def _skill_filters(stmt: Select, q: str | None, category: str | None) -> Select:
    """Apply the optional name/category filters to a skills query."""
    if q:
        stmt = stmt.where(Skill.name.ilike(f"%{q}%"))
    if category:
        stmt = stmt.where(Skill.category == category)
    return stmt


async def count_skills(
    session: AsyncSession, *, q: str | None = None, category: str | None = None
) -> int:
    stmt = _skill_filters(select(func.count()).select_from(Skill), q, category)
    return int((await session.execute(stmt)).scalar_one())


async def list_skills(
    session: AsyncSession,
    *,
    q: str | None = None,
    category: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[Skill]:
    stmt = _skill_filters(select(Skill), q, category)
    stmt = stmt.order_by(Skill.name).offset(offset).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


def _occupation_filters(stmt: Select, q: str | None, family: str | None) -> Select:
    """Apply the optional title/family filters to an occupations query."""
    if q:
        stmt = stmt.where(Occupation.title.ilike(f"%{q}%"))
    if family:
        stmt = stmt.where(Occupation.family == family)
    return stmt


async def count_occupations(
    session: AsyncSession, *, q: str | None = None, family: str | None = None
) -> int:
    stmt = _occupation_filters(select(func.count()).select_from(Occupation), q, family)
    return int((await session.execute(stmt)).scalar_one())


async def list_occupations(
    session: AsyncSession,
    *,
    q: str | None = None,
    family: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[Occupation]:
    stmt = _occupation_filters(select(Occupation), q, family)
    stmt = stmt.order_by(Occupation.title).offset(offset).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_occupation(session: AsyncSession, occupation_id: uuid.UUID) -> Occupation | None:
    stmt = select(Occupation).where(Occupation.id == occupation_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_occupation_skills(
    session: AsyncSession, occupation_id: uuid.UUID
) -> list[tuple[OccupationSkill, Skill]]:
    """Return (link, skill) rows for an occupation, most important first."""
    stmt = (
        select(OccupationSkill, Skill)
        .join(Skill, Skill.id == OccupationSkill.skill_id)
        .where(OccupationSkill.occupation_id == occupation_id)
        .order_by(OccupationSkill.importance.desc(), Skill.name)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1]) for row in rows]


async def list_transitions(
    session: AsyncSession, from_occupation_id: uuid.UUID
) -> list[tuple[OccupationTransition, Occupation]]:
    """Return (edge, to_occupation) rows out of an occupation, heaviest first."""
    stmt = (
        select(OccupationTransition, Occupation)
        .join(Occupation, Occupation.id == OccupationTransition.to_occupation_id)
        .where(OccupationTransition.from_occupation_id == from_occupation_id)
        .order_by(OccupationTransition.weight.desc())
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1]) for row in rows]
