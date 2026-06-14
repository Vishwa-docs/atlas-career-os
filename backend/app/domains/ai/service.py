"""Orchestration for Atlas's signature AI features.

The service resolves the current candidate, retrieves grounding context via the
RAG layer, builds prompts, calls the LLM for structured Glass-Box outputs, and
records token usage. Routers stay thin. Everything is resilient to sparse
profiles: when evidence is thin we still return an honest, low-confidence result
rather than failing.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domains.ai import prompts
from app.domains.ai.feature_schemas import (
    AtlasResponse,
    AtlasRoute,
    AtlasRouteProse,
    CoachReply,
    CurrentRole,
    FairPayProse,
    FairPayResponse,
    MarketBand,
    Negotiation,
    PivotProse,
    PivotResponse,
    PivotStepProse,
    RampStep,
    SalaryRange,
    SkillGap,
    TimeMonths,
    WeatherProse,
    WeatherResponse,
)
from app.domains.ai.feature_schemas import (
    Outlook as OutlookEnum,
)
from app.domains.ai.llm.client import ChatMessage, LLMClient
from app.domains.ai.rag import retrieval
from app.domains.ai.schemas import Citation, CitationSourceType, Confidence, GlassBox
from app.domains.ai.usage import record_usage
from app.domains.candidates.models import CandidateProfile

# Default median monthly salary anchors (MYR) by rough seniority, used only when
# an occupation has no recorded ``median_salary_myr``.
_DEFAULT_MEDIAN_BY_SENIORITY = {
    "junior": 3500,
    "mid": 6000,
    "senior": 11000,
}
_DEFAULT_MEDIAN = 6000


# --------------------------------------------------------------------------- #
# Candidate resolution
# --------------------------------------------------------------------------- #
async def resolve_candidate(session: AsyncSession, user_id: str) -> CandidateProfile:
    """Load the candidate profile for the signed-in user, or 404."""
    stmt = select(CandidateProfile).where(CandidateProfile.user_id == uuid.UUID(user_id))
    candidate = (await session.execute(stmt)).scalar_one_or_none()
    if candidate is None:
        raise NotFoundError("No candidate profile for this user.")
    return candidate


async def _record(
    session: AsyncSession,
    *,
    feature: str,
    result: Any,
    org_id: str | None,
    user_id: str | None,
) -> None:
    """Best-effort usage accounting; never fails the request."""
    usage = getattr(result, "usage", None)
    if usage is None:
        return
    try:
        await record_usage(
            session,
            feature=feature,
            model=getattr(result, "model", None) or "mock-or-azure",
            usage=usage,
            org_id=org_id,
            user_id=user_id,
        )
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- #
# Deterministic helpers (numbers computed in Python, never by the LLM)
# --------------------------------------------------------------------------- #
def _seniority_default_median(candidate: CandidateProfile) -> int:
    """A sensible salary anchor when an occupation has no recorded median."""
    years = float(getattr(candidate, "years_experience", 0.0) or 0.0)
    if years < 3:
        return _DEFAULT_MEDIAN_BY_SENIORITY["junior"]
    if years < 8:
        return _DEFAULT_MEDIAN_BY_SENIORITY["mid"]
    return _DEFAULT_MEDIAN_BY_SENIORITY["senior"]


def _resolve_median(occ: Any, candidate: CandidateProfile) -> int:
    """Occupation median if present, else a seniority-based default."""
    median = getattr(occ, "median_salary_myr", None) if occ else None
    return int(median) if median else _seniority_default_median(candidate)


def _confidence_band(score: float) -> Confidence:
    if score >= 0.66:
        return Confidence.HIGH
    if score >= 0.4:
        return Confidence.MEDIUM
    return Confidence.LOW


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


async def _prose(
    session: AsyncSession,
    *,
    llm: LLMClient,
    messages: list[ChatMessage],
    schema: type,
    feature: str,
    org_id: str | None,
    user_id: str | None,
    fallback: Any,
) -> Any:
    """Fetch prose-only output from the LLM; never fail the request on it.

    Mirrors the matching service: numbers are already computed, the model only
    writes the human text. Records best-effort token usage.
    """
    try:
        result = await llm.structured(messages, schema)
    except Exception:  # noqa: BLE001 - prose is non-critical; degrade gracefully
        return fallback
    await _record(session, feature=feature, result=result, org_id=org_id, user_id=user_id)
    return result


def _skill_gaps(
    occ_skills: list[dict[str, Any]],
    have_map: dict[str, float],
    *,
    limit: int = 6,
    threshold: float = 0.15,
) -> list[SkillGap]:
    """Top required skills the candidate does not strongly hold (have vs need)."""
    gaps: list[SkillGap] = []
    for s in occ_skills:
        need = _clamp01(float(s.get("level", 0.5)))
        have = _clamp01(float(have_map.get(s.get("skill_id", ""), 0.0)))
        if have + threshold < need:
            gaps.append(SkillGap(skill=s["skill"], have=round(have, 2), need=round(need, 2)))
        if len(gaps) >= limit:
            break
    return gaps


def _skill_coverage(occ_skills: list[dict[str, Any]], have_map: dict[str, float]) -> float:
    """How well the candidate covers a target occupation's skills (0..1)."""
    if not occ_skills:
        return 0.5
    total = 0.0
    weight = 0.0
    for s in occ_skills:
        need = max(0.01, _clamp01(float(s.get("level", 0.5))))
        imp = max(0.1, float(s.get("importance", 0.5)))
        have = _clamp01(float(have_map.get(s.get("skill_id", ""), 0.0)))
        total += imp * min(1.0, have / need)
        weight += imp
    return _clamp01(total / weight) if weight else 0.5


# --------------------------------------------------------------------------- #
# Coach
# --------------------------------------------------------------------------- #
async def coach_reply(
    session: AsyncSession,
    *,
    candidate: CandidateProfile,
    message: str,
    history: list[dict[str, str]] | None,
    llm: LLMClient,
    org_id: str | None,
    user_id: str | None,
) -> CoachReply:
    """A grounded, explainable coaching turn."""
    context = await retrieval.build_candidate_context(session, candidate)
    messages = prompts.build_coach_structured_messages(
        candidate_context=context, message=message, history=history
    )
    try:
        reply = await llm.structured(messages, CoachReply)
    except Exception:  # noqa: BLE001 - fall back to chat + a small Glass Box
        result = await llm.chat(messages)
        await record_usage(
            session,
            feature="ai.coach",
            model=result.model or "mock-or-azure",
            usage=result.usage,
            org_id=org_id,
            user_id=user_id,
        )
        await session.commit()
        return CoachReply(
            message=result.content,
            glass_box=GlassBox(
                rationale="General coaching guidance grounded in your profile.",
                confidence=Confidence.MEDIUM,
                confidence_score=0.55,
                citations=[
                    Citation(
                        label="Your career profile",
                        source_type=CitationSourceType.CAREER_HISTORY,
                    )
                ],
                what_would_change_this=["More detail about your goals and recent roles."],
                caveats=["This is coaching guidance, not a guarantee of outcomes."],
            ),
        )
    await _record(session, feature="ai.coach", result=reply, org_id=org_id, user_id=user_id)
    await session.commit()
    return reply


def build_coach_stream_messages(
    *, candidate_context: str, message: str, history: list[dict[str, str]] | None
) -> list[ChatMessage]:
    """Plain chat messages for the SSE streaming endpoint."""
    return prompts.build_coach_messages(
        candidate_context=candidate_context, message=message, history=history
    )


# --------------------------------------------------------------------------- #
# Trajectory Atlas
# --------------------------------------------------------------------------- #
async def trajectory_atlas(
    session: AsyncSession,
    *,
    candidate: CandidateProfile,
    horizon_years: int,
    llm: LLMClient,
    org_id: str | None,
    user_id: str | None,
) -> AtlasResponse:
    """Map realistic routes. Routes (titles, salaries, time, feasibility, demand,
    gaps) are computed in Python from the transition graph + the candidate's
    skills; the LLM only writes each route's trade_offs and Glass Box prose."""
    context = await retrieval.build_candidate_context(session, candidate)
    occ = await retrieval.get_occupation(session, candidate.current_occupation_id)
    current_title = getattr(occ, "title", None) or "your current role"

    transitions = await retrieval.realistic_transitions(
        session, candidate.current_occupation_id, limit=4
    )
    if not transitions:
        transitions = await retrieval.fallback_occupations(
            session,
            exclude_id=candidate.current_occupation_id,
            family=getattr(occ, "family", None),
            limit=4,
        )

    have_map = await retrieval.candidate_skill_map(session, candidate)
    max_weight = max((t["weight"] for t in transitions), default=0.0) or 1.0

    routes: list[AtlasRoute] = []
    for idx, tr in enumerate(transitions):
        try:
            target_id = uuid.UUID(tr["to_occupation_id"])
        except (ValueError, TypeError):
            continue
        target_occ = await retrieval.get_occupation(session, target_id)
        median = _resolve_median(target_occ, candidate)
        salary_range = SalaryRange(
            min=round(0.85 * median),
            median=median,
            max=round(1.25 * median),
            currency="MYR",
        )
        base_months = tr.get("median_months") or 24
        time_months = TimeMonths(
            min=max(1, int(base_months) - 6), max=int(base_months) + 12
        )

        occ_skills = await retrieval.occupation_skills(session, target_id, limit=20)
        coverage = _skill_coverage(occ_skills, have_map)
        norm_weight = tr["weight"] / max_weight if max_weight else 0.0
        feasibility = round(_clamp01(0.55 * norm_weight + 0.45 * coverage), 2)

        avg_trend = await retrieval.occupation_demand_trend(session, target_id)
        demand_trend = round(avg_trend, 3) if avg_trend is not None else 0.0
        skill_gaps = _skill_gaps(occ_skills, have_map)

        facts = (
            f"Target role: {tr['title']}\n"
            f"Salary band (MYR/month): min {salary_range.min}, median "
            f"{salary_range.median}, max {salary_range.max}\n"
            f"Time to reach: {time_months.min}-{time_months.max} months\n"
            f"Feasibility (0-1): {feasibility:.2f} "
            f"(transition weight {tr['weight']:.2f}, skill coverage {coverage:.2f})\n"
            f"Demand trend: {demand_trend:+.2f}\n"
            "Skill gaps (have vs need): "
            + (
                "; ".join(f"{g.skill} {g.have:.1f}->{g.need:.1f}" for g in skill_gaps)
                or "(none significant)"
            )
            + f"\nHorizon: {horizon_years} year(s)"
        )
        prose: AtlasRouteProse = await _prose(
            session,
            llm=llm,
            messages=prompts.build_atlas_prose_messages(
                candidate_context=context,
                current_occupation=current_title,
                route_title=tr["title"],
                facts=facts,
            ),
            schema=AtlasRouteProse,
            feature="ai.atlas",
            org_id=org_id,
            user_id=user_id,
            fallback=AtlasRouteProse(
                rationale=(
                    f"Moving toward {tr['title']} is a realistic route given the "
                    "observed transition graph and your current skills."
                ),
                trade_offs=["Weigh the ramp-up time against the salary upside."],
            ),
        )

        routes.append(
            AtlasRoute(
                id=f"route-{idx + 1}",
                title=tr["title"],
                occupation_id=tr["to_occupation_id"],
                salary_range=salary_range,
                time_months=time_months,
                feasibility=feasibility,
                demand_trend=demand_trend,
                skill_gaps=skill_gaps,
                trade_offs=prose.trade_offs,
                glass_box=GlassBox(
                    rationale=prose.rationale
                    or f"A realistic route toward {tr['title']}.",
                    confidence=_confidence_band(feasibility),
                    confidence_score=feasibility,
                    citations=[
                        retrieval.transition_citation(transitions),
                        retrieval.salary_citation(target_occ),
                    ],
                    what_would_change_this=prose.what_would_change_this
                    or ["Closing the listed skill gaps would raise feasibility."],
                    caveats=prose.caveats
                    or ["Salary bands are market anchors, not offers."],
                ),
            )
        )

    overall = round(sum(r.feasibility for r in routes) / len(routes), 2) if routes else 0.3
    response = AtlasResponse(
        current=CurrentRole(
            occupation=current_title,
            occupation_id=(
                str(candidate.current_occupation_id)
                if candidate.current_occupation_id
                else None
            ),
        ),
        routes=routes,
        glass_box=GlassBox(
            rationale=(
                f"Mapped {len(routes)} realistic route(s) from {current_title} over "
                f"the next {horizon_years} year(s), grounded in the observed "
                "transition graph and your recorded skills."
                if routes
                else (
                    "No realistic routes could be derived yet — add your current "
                    "occupation and skills to unlock the trajectory map."
                )
            ),
            confidence=_confidence_band(overall),
            confidence_score=overall,
            citations=[retrieval.transition_citation(transitions)],
            what_would_change_this=[
                "Confirming your current occupation sharpens the route graph.",
                "More verified skills refine feasibility and gaps.",
            ],
            caveats=[
                "Routes reflect typical market moves, not guaranteed outcomes.",
            ],
        ),
    )
    await session.commit()
    return response


# --------------------------------------------------------------------------- #
# Fair Pay
# --------------------------------------------------------------------------- #
async def fair_pay(
    session: AsyncSession,
    *,
    candidate: CandidateProfile,
    occupation_id: uuid.UUID | None,
    current_pay: int | None,
    llm: LLMClient,
    org_id: str | None,
    user_id: str | None,
) -> FairPayResponse:
    occ_id = occupation_id or candidate.current_occupation_id or candidate.target_occupation_id
    occ = await retrieval.get_occupation(session, occ_id)
    role = getattr(occ, "title", None) or "your role"
    location = candidate.location or "Malaysia"
    context = await retrieval.build_candidate_context(session, candidate)

    # --- numbers computed in Python ---
    has_anchor = bool(getattr(occ, "median_salary_myr", None)) if occ else False
    p50 = _resolve_median(occ, candidate)
    market = MarketBand(
        p25=round(0.82 * p50), p50=p50, p75=round(1.25 * p50), currency="MYR"
    )
    gap_pct: float | None = None
    if current_pay is not None and p50:
        gap_pct = round((current_pay - p50) / p50 * 100, 1)

    if gap_pct is None:
        verdict = "Insufficient data — share your current pay for a verdict"
    elif gap_pct < -8:
        verdict = "Underpaid vs market"
    elif gap_pct > 10:
        verdict = "Above market"
    else:
        verdict = "In the fair range"

    # confidence: high when we have a real anchor AND the user's pay; low when sparse.
    conf_score = 0.8 if (has_anchor and current_pay is not None) else 0.55 if has_anchor else 0.3

    facts = (
        f"Role: {role}\nLocation: {location}\n"
        f"Market band (MYR/month): p25 {market.p25}, p50 {market.p50}, p75 {market.p75}"
        + (" (DOSM anchor)" if has_anchor else " (seniority-based default — no anchor)")
        + "\n"
        + (
            f"Your current pay: MYR {current_pay}/month; gap vs median: {gap_pct:+.1f}%"
            if current_pay is not None
            else "Current pay not provided."
        )
        + f"\nVerdict: {verdict}"
    )
    prose: FairPayProse = await _prose(
        session,
        llm=llm,
        messages=prompts.build_fair_pay_prose_messages(
            role=role, location=location, facts=facts, candidate_context=context
        ),
        schema=FairPayProse,
        feature="ai.fair_pay",
        org_id=org_id,
        user_id=user_id,
        fallback=FairPayProse(
            rationale=f"Benchmarked against the market median of MYR {market.p50}/month.",
            timing="Raise pay at your next review or after a clear win.",
            script="Anchor on the market median and your delivered impact.",
            talking_points=[
                f"Market median for {role} is around MYR {market.p50}/month.",
                "Tie the ask to recent, quantifiable results.",
            ],
        ),
    )

    response = FairPayResponse(
        role=role,
        location=location,
        market=market,
        your_pay=current_pay,
        gap_pct=gap_pct,
        verdict=verdict,
        negotiation=Negotiation(
            timing=prose.timing or "Time the conversation around your next review.",
            script=prose.script
            or "Anchor on the market median and your delivered impact.",
            talking_points=prose.talking_points
            or [f"Market median for {role} is around MYR {market.p50}/month."],
        ),
        glass_box=GlassBox(
            rationale=prose.rationale
            or f"Benchmarked against the market median of MYR {market.p50}/month.",
            confidence=_confidence_band(conf_score),
            confidence_score=conf_score,
            citations=[
                Citation(
                    label="OpenDOSM formal-sector wages (anchor)",
                    source_type=CitationSourceType.SALARY_DATA,
                    source_id=str(getattr(occ, "id", "")) or None,
                    snippet=(
                        f"Median ≈ MYR {market.p50}/month for {role}"
                        if has_anchor
                        else f"No DOSM anchor; seniority default MYR {market.p50}/month"
                    ),
                )
            ],
            what_would_change_this=prose.what_would_change_this
            or [
                "Sharing your exact current pay sharpens the gap estimate.",
                "A more specific occupation match refines the band.",
            ],
            caveats=prose.caveats
            or [
                "Bands are market anchors for the role, not a personalised offer.",
                *([] if has_anchor else ["No salary anchor for this role — low confidence."]),
            ],
        ),
    )
    await session.commit()
    return response


# --------------------------------------------------------------------------- #
# Career Weather
# --------------------------------------------------------------------------- #
async def career_weather(
    session: AsyncSession,
    *,
    candidate: CandidateProfile,
    occupation_id: uuid.UUID | None,
    region: str | None,
    llm: LLMClient,
    org_id: str | None,
    user_id: str | None,
) -> WeatherResponse:
    occ_id = occupation_id or candidate.current_occupation_id
    occ = await retrieval.get_occupation(session, occ_id)
    role = getattr(occ, "title", None) or "your role"
    region_name = region or candidate.location or "Malaysia"

    # --- numbers computed in Python from skill demand signals ---
    trends = await retrieval.skill_trends(session, occ_id)
    rising = trends["rising"][:6]
    cooling = trends["cooling"][:6]
    avg_trend = await retrieval.occupation_demand_trend(session, occ_id)
    has_signal = avg_trend is not None
    avg_trend = avg_trend or 0.0

    # demand_index: map an avg trend in roughly [-1, 1] onto 0..100, centred at 50.
    demand_index = round(_clamp01((avg_trend + 1.0) / 2.0) * 100, 1)
    if avg_trend > 0.1:
        outlook = OutlookEnum.SUNNY
    elif avg_trend < -0.1:
        outlook = OutlookEnum.STORMY
    else:
        outlook = OutlookEnum.CLOUDY
    # salary_drift: small derived figure tracking the demand signal.
    salary_drift_pct = round(avg_trend * 5.0, 1)
    conf_score = 0.7 if has_signal else 0.3

    facts = (
        f"Role: {role}\nRegion: {region_name}\n"
        f"Outlook: {outlook.value}\n"
        f"Demand index (0-100): {demand_index}\n"
        f"Average skill-demand trend: {avg_trend:+.2f}\n"
        f"Estimated salary drift: {salary_drift_pct:+.1f}%\n"
        f"Rising-demand skills: {', '.join(rising) or '(none observed)'}\n"
        f"Cooling-demand skills: {', '.join(cooling) or '(none observed)'}"
    )
    prose: WeatherProse = await _prose(
        session,
        llm=llm,
        messages=prompts.build_weather_prose_messages(
            role=role, region=region_name, facts=facts
        ),
        schema=WeatherProse,
        feature="ai.weather",
        org_id=org_id,
        user_id=user_id,
        fallback=WeatherProse(
            rationale="Outlook derived from aggregated skill-demand signals for the role.",
            summary=(
                f"Demand for {role} skills looks {outlook.value}; "
                f"rising areas: {', '.join(rising[:3]) or 'none clearly observed'}."
            ),
        ),
    )

    response = WeatherResponse(
        role=role,
        region=region_name,
        outlook=outlook,
        summary=prose.summary
        or f"The outlook for {role} in {region_name} is {outlook.value}.",
        demand_index=demand_index,
        rising_skills=rising,
        cooling_skills=cooling,
        salary_drift_pct=salary_drift_pct,
        glass_box=GlassBox(
            rationale=prose.rationale
            or "Outlook derived from aggregated skill-demand signals for the role.",
            confidence=_confidence_band(conf_score),
            confidence_score=conf_score,
            citations=[
                Citation(
                    label="Skill demand signals (labour market)",
                    source_type=CitationSourceType.LABOR_MARKET,
                    source_id=str(getattr(occ, "id", "")) or None,
                    snippet=(
                        f"Avg skill-demand trend {avg_trend:+.2f}; rising: "
                        f"{', '.join(rising[:4]) or '(none)'}"
                    ),
                )
            ],
            what_would_change_this=prose.what_would_change_this
            or ["Fresh labour-market signals would shift the outlook."],
            caveats=prose.caveats
            or (
                ["This describes the current landscape, not a forecast."]
                if has_signal
                else ["No demand signals for this role yet — low confidence."]
            ),
        ),
    )
    await session.commit()
    return response


# --------------------------------------------------------------------------- #
# Pivot feasibility
# --------------------------------------------------------------------------- #
async def pivot(
    session: AsyncSession,
    *,
    candidate: CandidateProfile,
    target_occupation_id: uuid.UUID,
    llm: LLMClient,
    org_id: str | None,
    user_id: str | None,
) -> PivotResponse:
    target = await retrieval.get_occupation(session, target_occupation_id)
    if target is None:
        raise NotFoundError("Target occupation not found.")
    target_title = getattr(target, "title", "the target role")
    context = await retrieval.build_candidate_context(session, candidate)

    # --- numbers computed in Python ---
    target_skills = await retrieval.occupation_skills(session, target_occupation_id, limit=20)
    have_map = await retrieval.candidate_skill_map(session, candidate)
    gap = _skill_gaps(target_skills, have_map, limit=10)
    coverage = _skill_coverage(target_skills, have_map)

    transition = await retrieval.find_transition(
        session, candidate.current_occupation_id, target_occupation_id
    )
    norm_weight = _clamp01(transition["weight"]) if transition else 0.0
    feasibility = round(_clamp01(0.55 * norm_weight + 0.45 * coverage), 2)

    facts = (
        f"Target role: {target_title}\n"
        f"Feasibility (0-1): {feasibility:.2f} "
        f"(transition weight {norm_weight:.2f}, skill coverage {coverage:.2f})\n"
        + (
            f"Observed transition: ~{transition.get('median_months') or '?'} months, "
            f"salary delta {transition.get('salary_delta_pct')}%\n"
            if transition
            else "No direct observed transition from your current role.\n"
        )
        + "Skill gaps (have vs need): "
        + (
            "; ".join(f"{g.skill} {g.have:.1f}->{g.need:.1f}" for g in gap)
            or "(none significant)"
        )
    )
    prose: PivotProse = await _prose(
        session,
        llm=llm,
        messages=prompts.build_pivot_prose_messages(
            candidate_context=context, target_occupation=target_title, facts=facts
        ),
        schema=PivotProse,
        feature="ai.pivot",
        org_id=org_id,
        user_id=user_id,
        fallback=PivotProse(
            rationale=(
                f"Pivot feasibility into {target_title} reflects your skill coverage "
                "and the observed transition graph."
            ),
            ramp_steps=[
                PivotStepProse(
                    step=f"Close the gap on {gap[0].skill}" if gap else "Confirm core skills",
                    resource="A focused course or hands-on project",
                )
            ],
        ),
    )

    # Build ramp steps: pair LLM prose steps with a deterministic months estimate.
    base_months = (transition or {}).get("median_months") or 18
    per_step = max(2, int(base_months) // max(1, len(prose.ramp_steps) or len(gap) or 1))
    ramp: list[RampStep] = []
    for i, ps in enumerate(prose.ramp_steps or []):
        ramp.append(
            RampStep(
                step=ps.step or f"Step {i + 1}",
                resource=ps.resource or "A relevant course or project",
                months=per_step,
            )
        )
    if not ramp:
        ramp = [
            RampStep(
                step=f"Build {g.skill} to the required level",
                resource="A focused course or hands-on project",
                months=per_step,
            )
            for g in gap[:3]
        ]

    response = PivotResponse(
        feasibility=feasibility,
        gap=gap,
        ramp=ramp,
        glass_box=GlassBox(
            rationale=prose.rationale
            or (
                f"Pivot feasibility into {target_title} reflects your skill coverage "
                "and the observed transition graph."
            ),
            confidence=_confidence_band(feasibility),
            confidence_score=feasibility,
            citations=[
                Citation(
                    label="Target role skill requirements",
                    source_type=CitationSourceType.SKILL_TAXONOMY,
                    source_id=str(target_occupation_id),
                    snippet=", ".join(s["skill"] for s in target_skills[:8])
                    or "(no skill profile)",
                ),
                Citation(
                    label="Observed transition into target (labour market)",
                    source_type=CitationSourceType.LABOR_MARKET,
                    snippet=(
                        f"Transition weight {norm_weight:.2f}"
                        if transition
                        else "No direct observed transition"
                    ),
                ),
            ],
            what_would_change_this=prose.what_would_change_this
            or ["Closing the listed skill gaps would raise feasibility."],
            caveats=prose.caveats
            or ["Feasibility reflects typical moves, not a guaranteed outcome."],
        ),
    )
    await session.commit()
    return response
