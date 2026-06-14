"""AI feature endpoints — thin HTTP layer over the AI service.

All endpoints are authenticated and resolve the current candidate from the
principal. Every structured response embeds a Glass Box, and every call records
token usage attributable to the org/user.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import orjson
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_current_principal, get_session
from app.domains.ai import service
from app.domains.ai.feature_schemas import (
    AtlasResponse,
    CoachReply,
    FairPayResponse,
    PivotResponse,
    WeatherResponse,
)
from app.domains.ai.llm.factory import get_llm
from app.domains.ai.rag import retrieval
from app.domains.ai.usage import record_usage

router = APIRouter(prefix="/ai", tags=["ai"])


# --------------------------------------------------------------------------- #
# Request bodies
# --------------------------------------------------------------------------- #
class CoachRequest(BaseModel):
    message: str
    history: list[dict[str, str]] | None = None


class AtlasRequest(BaseModel):
    horizon_years: int | None = 5


class FairPayRequest(BaseModel):
    occupation_id: str | None = None
    current_pay: int | None = None


class WeatherRequest(BaseModel):
    occupation_id: str | None = None
    region: str | None = None


class PivotRequest(BaseModel):
    target_occupation_id: str


def _opt_uuid(value: str | None) -> uuid.UUID | None:
    return uuid.UUID(value) if value else None


# --------------------------------------------------------------------------- #
# Coach
# --------------------------------------------------------------------------- #
@router.post("/coach", response_model=CoachReply)
async def coach(
    body: CoachRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> CoachReply:
    candidate = await service.resolve_candidate(session, principal.user_id)
    return await service.coach_reply(
        session,
        candidate=candidate,
        message=body.message,
        history=body.history,
        llm=get_llm(),
        org_id=principal.org_id,
        user_id=principal.user_id,
    )


@router.post("/coach/stream")
async def coach_stream(
    body: CoachRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Server-Sent Events stream of coach deltas."""
    candidate = await service.resolve_candidate(session, principal.user_id)
    context = await retrieval.build_candidate_context(session, candidate)
    messages = service.build_coach_stream_messages(
        candidate_context=context, message=body.message, history=body.history
    )
    llm = get_llm()
    org_id, user_id = principal.org_id, principal.user_id

    async def event_source() -> AsyncIterator[bytes]:
        char_count = 0
        try:
            async for delta in llm.stream_chat(messages):
                char_count += len(delta)
                frame = orjson.dumps({"delta": delta}).decode()
                yield f"data: {frame}\n\n".encode()
        except Exception:  # noqa: BLE001 - end the stream cleanly on error
            err = orjson.dumps({"error": "stream interrupted"}).decode()
            yield f"data: {err}\n\n".encode()
        finally:
            yield b"data: [DONE]\n\n"
            # Record an approximate usage row for the streamed completion.
            try:
                from app.domains.ai.llm.client import TokenUsage

                await record_usage(
                    session,
                    feature="ai.coach.stream",
                    model="mock-or-azure",
                    usage=TokenUsage(completion_tokens=max(1, char_count // 4)),
                    org_id=org_id,
                    user_id=user_id,
                )
                await session.commit()
            except Exception:  # noqa: BLE001
                pass

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --------------------------------------------------------------------------- #
# Trajectory Atlas
# --------------------------------------------------------------------------- #
@router.post("/atlas", response_model=AtlasResponse)
async def atlas(
    body: AtlasRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> AtlasResponse:
    candidate = await service.resolve_candidate(session, principal.user_id)
    return await service.trajectory_atlas(
        session,
        candidate=candidate,
        horizon_years=body.horizon_years or 5,
        llm=get_llm(),
        org_id=principal.org_id,
        user_id=principal.user_id,
    )


# --------------------------------------------------------------------------- #
# Fair Pay
# --------------------------------------------------------------------------- #
@router.post("/fair-pay", response_model=FairPayResponse)
async def fair_pay(
    body: FairPayRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> FairPayResponse:
    candidate = await service.resolve_candidate(session, principal.user_id)
    return await service.fair_pay(
        session,
        candidate=candidate,
        occupation_id=_opt_uuid(body.occupation_id),
        current_pay=body.current_pay,
        llm=get_llm(),
        org_id=principal.org_id,
        user_id=principal.user_id,
    )


# --------------------------------------------------------------------------- #
# Career Weather
# --------------------------------------------------------------------------- #
@router.post("/weather", response_model=WeatherResponse)
async def weather(
    body: WeatherRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> WeatherResponse:
    candidate = await service.resolve_candidate(session, principal.user_id)
    return await service.career_weather(
        session,
        candidate=candidate,
        occupation_id=_opt_uuid(body.occupation_id),
        region=body.region,
        llm=get_llm(),
        org_id=principal.org_id,
        user_id=principal.user_id,
    )


# --------------------------------------------------------------------------- #
# Pivot
# --------------------------------------------------------------------------- #
@router.post("/pivot", response_model=PivotResponse)
async def pivot(
    body: PivotRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> PivotResponse:
    candidate = await service.resolve_candidate(session, principal.user_id)
    return await service.pivot(
        session,
        candidate=candidate,
        target_occupation_id=uuid.UUID(body.target_occupation_id),
        llm=get_llm(),
        org_id=principal.org_id,
        user_id=principal.user_id,
    )
