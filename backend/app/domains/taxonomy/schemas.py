"""Read schemas for the taxonomy domain (skills, occupations, transitions).

The taxonomy is the shared vocabulary of the Career Graph. These schemas are
read-only projections of the ORM models, plus the composite ``OccupationDetail``
(occupation + its skill requirements) and the ``OccupationTransitionEdge`` that
powers the "realistic next moves" graph.
"""

from __future__ import annotations

import uuid

from pydantic import Field

from app.core.schemas import ORMModel


class SkillRead(ORMModel):
    """A skill in the taxonomy."""

    id: uuid.UUID
    name: str
    slug: str
    category: str | None = None
    description: str | None = None
    demand_trend: float = 0.0


class OccupationRead(ORMModel):
    """An occupation in the taxonomy (list/summary view)."""

    id: uuid.UUID
    title: str
    slug: str
    isco_code: str | None = None
    masco_code: str | None = None
    family: str | None = None
    typical_education: str | None = None
    median_salary_myr: int | None = None
    description: str | None = None


class OccupationSkillRead(ORMModel):
    """A skill requirement on an occupation, with its weighting."""

    skill: SkillRead
    importance: float = Field(ge=0.0, le=1.0)
    level: float = Field(ge=0.0, le=1.0)
    essential: bool = True


class OccupationDetail(ORMModel):
    """Occupation plus its skill requirements and salary anchor."""

    occupation: OccupationRead
    skills: list[OccupationSkillRead] = Field(default_factory=list)
    median_salary_myr: int | None = None


class OccupationTransitionEdge(ORMModel):
    """A weighted "realistic next move" edge out of an occupation."""

    to_occupation: OccupationRead
    weight: float
    median_months: int | None = None
    median_salary_delta_pct: float | None = None
