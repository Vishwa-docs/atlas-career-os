"""Taxonomy HTTP routes — read-only, any authenticated user.

Thin layer: parse params, delegate to the service, return schemas. Mounted by
the API aggregator under ``/api/v1`` (so the prefix below becomes
``/api/v1/taxonomy``).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_current_principal, get_session
from app.core.schemas import Page, PageParams
from app.domains.taxonomy import service
from app.domains.taxonomy.schemas import (
    OccupationDetail,
    OccupationRead,
    OccupationTransitionEdge,
    SkillRead,
)

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


@router.get("/skills", response_model=Page[SkillRead])
async def list_skills(
    q: str | None = Query(None, description="Case-insensitive name fragment."),
    category: str | None = Query(None, description="Exact skill category."),
    page_params: PageParams = Depends(),
    session: AsyncSession = Depends(get_session),
    _: Principal = Depends(get_current_principal),
) -> Page[SkillRead]:
    """List skills in the taxonomy, optionally filtered by name and category."""
    return await service.list_skills(
        session,
        q=q,
        category=category,
        page=page_params.page,
        page_size=page_params.page_size,
        offset=page_params.offset,
    )


@router.get("/occupations", response_model=Page[OccupationRead])
async def list_occupations(
    q: str | None = Query(None, description="Case-insensitive title fragment."),
    family: str | None = Query(None, description="Exact occupation family."),
    page_params: PageParams = Depends(),
    session: AsyncSession = Depends(get_session),
    _: Principal = Depends(get_current_principal),
) -> Page[OccupationRead]:
    """List occupations in the taxonomy, optionally filtered by title and family."""
    return await service.list_occupations(
        session,
        q=q,
        family=family,
        page=page_params.page,
        page_size=page_params.page_size,
        offset=page_params.offset,
    )


@router.get("/occupations/{occupation_id}", response_model=OccupationDetail)
async def get_occupation(
    occupation_id: str,
    session: AsyncSession = Depends(get_session),
    _: Principal = Depends(get_current_principal),
) -> OccupationDetail:
    """Return an occupation with its skill requirements and median salary."""
    return await service.get_occupation_detail(session, uuid.UUID(occupation_id))


@router.get(
    "/occupations/{occupation_id}/transitions",
    response_model=list[OccupationTransitionEdge],
)
async def list_occupation_transitions(
    occupation_id: str,
    session: AsyncSession = Depends(get_session),
    _: Principal = Depends(get_current_principal),
) -> list[OccupationTransitionEdge]:
    """Return the "realistic next moves" out of an occupation, weight desc."""
    return await service.list_transitions(session, uuid.UUID(occupation_id))
