"""Prompt builders for Atlas's AI features.

Each function returns a ``list[ChatMessage]`` that begins with the shared
:data:`SYSTEM_PREAMBLE`, injects already-retrieved grounding context, and
instructs the model to fill the relevant structured schema *honestly* — with
ranges (not false precision), a calibrated confidence, citations to the provided
evidence, and explicit caveats. Untrusted free text is fenced upstream by the
RAG layer / guardrails; builders just compose.
"""

from __future__ import annotations

from typing import Any

from app.domains.ai.guardrails import SYSTEM_PREAMBLE, wrap_untrusted
from app.domains.ai.llm.client import ChatMessage

_HONESTY = (
    "Fill the requested structured schema. Every numeric estimate must be a "
    "realistic RANGE grounded in the provided evidence — never invent figures, "
    "employers, or skills. Set the glass_box: a plain-language rationale, a "
    "confidence band (low/medium/high) with a calibrated 0–1 score, citations to "
    "the evidence below, what_would_change_this, and honest caveats. If the "
    "profile is sparse, return a sensible LOW-confidence answer and say so."
)


def _sys() -> ChatMessage:
    return ChatMessage(role="system", content=SYSTEM_PREAMBLE)


# --------------------------------------------------------------------------- #
# Coach (conversational co-pilot)
# --------------------------------------------------------------------------- #
def build_coach_messages(
    *,
    candidate_context: str,
    message: str,
    history: list[dict[str, str]] | None = None,
) -> list[ChatMessage]:
    """Compose a coaching turn grounded in the candidate's profile."""
    msgs: list[ChatMessage] = [_sys()]
    msgs.append(
        ChatMessage(
            role="system",
            content=(
                "You are the user's career coach. Be concrete and kind, reason over "
                "the profile context below, and never fabricate facts.\n\n"
                f"PROFILE CONTEXT:\n{candidate_context}"
            ),
        )
    )
    for turn in history or []:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            # User-authored turns are untrusted; assistant turns are ours.
            safe = wrap_untrusted(content, kind="prior_user_turn") if role == "user" else content
            msgs.append(ChatMessage(role=role, content=safe))
    msgs.append(ChatMessage(role="user", content=wrap_untrusted(message, kind="user_message")))
    return msgs


def build_coach_structured_messages(
    *,
    candidate_context: str,
    message: str,
    history: list[dict[str, str]] | None = None,
) -> list[ChatMessage]:
    """Coach messages that also ask for a CoachReply Glass Box."""
    msgs = build_coach_messages(
        candidate_context=candidate_context, message=message, history=history
    )
    msgs.append(
        ChatMessage(
            role="user",
            content=(
                "Reply in the 'message' field, then fill the glass_box explaining "
                "what in the profile you grounded the advice on. " + _HONESTY
            ),
        )
    )
    return msgs


# --------------------------------------------------------------------------- #
# Trajectory Atlas
# --------------------------------------------------------------------------- #
def build_atlas_messages(
    *,
    candidate_context: str,
    current_occupation: str,
    transitions: list[dict[str, Any]],
    horizon_years: int,
) -> list[ChatMessage]:
    facts = _render_transitions(transitions)
    return [
        _sys(),
        ChatMessage(
            role="user",
            content=(
                "Map 2–4 realistic career routes for this person over the next "
                f"{horizon_years} year(s). Ground each route in the OBSERVED "
                "TRANSITIONS below — prefer moves that actually happen in the "
                "market. For each route give a salary RANGE, a time-to-reach range "
                "in months, a feasibility 0–1, the demand_trend, the concrete "
                "skill_gaps (have vs need), and the trade_offs.\n\n"
                f"CURRENT OCCUPATION: {current_occupation}\n"
                f"OBSERVED TRANSITIONS:\n{facts}\n\n"
                f"{candidate_context}\n\n" + _HONESTY
            ),
        ),
    ]


# --------------------------------------------------------------------------- #
# Fair Pay
# --------------------------------------------------------------------------- #
def build_fair_pay_messages(
    *,
    role: str,
    location: str,
    median_salary_myr: int | None,
    current_pay: int | None,
    candidate_context: str,
) -> list[ChatMessage]:
    anchor = (
        f"OpenDOSM median monthly salary anchor: MYR {median_salary_myr}. "
        f"Starting heuristic band — p25≈{int(median_salary_myr * 0.8)}, "
        f"p50≈{median_salary_myr}, p75≈{int(median_salary_myr * 1.25)} "
        "(you may adjust within reason given the evidence)."
        if median_salary_myr
        else "No salary anchor available — return a LOW-confidence estimate."
    )
    pay_line = (
        f"The user's current pay is MYR {current_pay}/month."
        if current_pay
        else "The user did not share their current pay."
    )
    return [
        _sys(),
        ChatMessage(
            role="user",
            content=(
                f"Benchmark fair pay for a {role} in {location}. Produce a market "
                "band (p25/p50/p75), compute gap_pct if current pay is known, give "
                "a one-line verdict, and a negotiation plan (timing, a short script, "
                "talking_points) grounded in evidence.\n\n"
                f"{anchor}\n{pay_line}\n\n"
                f"{candidate_context}\n\n" + _HONESTY
            ),
        ),
    ]


# --------------------------------------------------------------------------- #
# Career Weather
# --------------------------------------------------------------------------- #
def build_weather_messages(
    *,
    role: str,
    region: str,
    rising_skills: list[str],
    cooling_skills: list[str],
    median_salary_myr: int | None,
) -> list[ChatMessage]:
    return [
        _sys(),
        ChatMessage(
            role="user",
            content=(
                f"Give the 'career weather' for a {role} in {region}: an outlook "
                "(sunny|cloudy|stormy), a short summary, a demand_index 0–1, the "
                "rising_skills and cooling_skills, and an estimated salary_drift_pct. "
                "Ground rising/cooling strictly in the skill demand signals below; "
                "do NOT predict the future — describe the current landscape.\n\n"
                f"Rising-demand skills: {', '.join(rising_skills) or '(none observed)'}\n"
                f"Cooling-demand skills: {', '.join(cooling_skills) or '(none observed)'}\n"
                f"Median salary anchor (MYR/month): {median_salary_myr or 'unknown'}\n\n" + _HONESTY
            ),
        ),
    ]


# --------------------------------------------------------------------------- #
# Pivot feasibility
# --------------------------------------------------------------------------- #
def build_pivot_messages(
    *,
    candidate_context: str,
    target_occupation: str,
    target_skills: list[dict[str, Any]],
    transition: dict[str, Any] | None,
) -> list[ChatMessage]:
    needed = (
        ", ".join(f"{s['skill']} (importance {s['importance']:.1f})" for s in target_skills[:15])
        or "(no skill profile available)"
    )
    tr = (
        f"Observed transition into this role: weight {transition['weight']:.2f}, "
        f"median {transition.get('median_months') or '?'} months, "
        f"salary delta {transition.get('salary_delta_pct')}%."
        if transition
        else "No direct observed transition into this role from the current one."
    )
    return [
        _sys(),
        ChatMessage(
            role="user",
            content=(
                f"Assess the feasibility (0–1) of pivoting into '{target_occupation}'. "
                "List the skill gap (have vs need) and a concrete ramp plan "
                "(ordered steps, each with a resource and a months estimate). Ground "
                "everything in the role's skill needs and the transition evidence.\n\n"
                f"TARGET ROLE SKILLS: {needed}\n{tr}\n\n"
                f"{candidate_context}\n\n" + _HONESTY
            ),
        ),
    ]


# --------------------------------------------------------------------------- #
# Prose-only builders
#
# These mirror the matching-service pattern: the numbers are ALREADY computed in
# Python and must NOT be changed by the model. The model only writes the human
# prose (rationale, caveats, trade-offs, negotiation script, etc.) grounded in
# those fixed figures. The service then assembles the final response object.
# --------------------------------------------------------------------------- #
_PROSE_RULES = (
    "The numeric and factual fields shown above are ALREADY computed from real "
    "data and must NOT be changed — only explain them honestly in plain language. "
    "Write a calibrated rationale, concrete what_would_change_this factors, and "
    "honest caveats. Never invent figures, employers, or skills."
)


def build_atlas_prose_messages(
    *,
    candidate_context: str,
    current_occupation: str,
    route_title: str,
    facts: str,
) -> list[ChatMessage]:
    """Ask the model to explain ONE already-computed Atlas route."""
    return [
        _sys(),
        ChatMessage(
            role="user",
            content=(
                f"Explain this career route from '{current_occupation}' to "
                f"'{route_title}'. Provide the trade_offs of taking it, plus the "
                "glass_box prose.\n\n"
                f"COMPUTED ROUTE FACTS (fixed):\n{facts}\n\n"
                f"{candidate_context}\n\n" + _PROSE_RULES
            ),
        ),
    ]


def build_fair_pay_prose_messages(
    *,
    role: str,
    location: str,
    facts: str,
    candidate_context: str,
) -> list[ChatMessage]:
    """Ask the model for negotiation prose around an already-computed pay band."""
    return [
        _sys(),
        ChatMessage(
            role="user",
            content=(
                f"A fair-pay benchmark for a {role} in {location} has already been "
                "computed below. Write the negotiation plan (timing, a short script, "
                "talking_points) and the glass_box prose grounded in those figures.\n\n"
                f"COMPUTED PAY FACTS (fixed):\n{facts}\n\n"
                f"{candidate_context}\n\n" + _PROSE_RULES
            ),
        ),
    ]


def build_weather_prose_messages(
    *,
    role: str,
    region: str,
    facts: str,
) -> list[ChatMessage]:
    """Ask the model to summarise an already-computed 'career weather' reading."""
    return [
        _sys(),
        ChatMessage(
            role="user",
            content=(
                f"The 'career weather' for a {role} in {region} has been computed "
                "below from skill-demand signals. Write a short summary and the "
                "glass_box prose. Describe the current landscape — do NOT predict the "
                f"future.\n\nCOMPUTED WEATHER FACTS (fixed):\n{facts}\n\n" + _PROSE_RULES
            ),
        ),
    ]


def build_pivot_prose_messages(
    *,
    candidate_context: str,
    target_occupation: str,
    facts: str,
) -> list[ChatMessage]:
    """Ask the model for a ramp plan around an already-computed pivot feasibility."""
    return [
        _sys(),
        ChatMessage(
            role="user",
            content=(
                f"A pivot into '{target_occupation}' has been assessed below "
                "(feasibility and skill gap are fixed). Propose a concrete, ordered "
                "ramp plan as ramp_steps (each with a step description and a learning "
                "resource), plus the glass_box prose.\n\n"
                f"COMPUTED PIVOT FACTS (fixed):\n{facts}\n\n"
                f"{candidate_context}\n\n" + _PROSE_RULES
            ),
        ),
    ]


# --------------------------------------------------------------------------- #
# Internal
# --------------------------------------------------------------------------- #
def _render_transitions(transitions: list[dict[str, Any]]) -> str:
    if not transitions:
        return "  (no observed transitions for this occupation)"
    out = []
    for t in transitions:
        out.append(
            f"  - {t['title']}: weight {t['weight']:.2f}, "
            f"~{t.get('median_months') or '?'} months, "
            f"salary delta {t.get('salary_delta_pct')}%, "
            f"target median MYR {t.get('median_salary_myr') or '?'}"
        )
    return "\n".join(out)


__all__ = [
    "build_coach_messages",
    "build_coach_structured_messages",
    "build_atlas_messages",
    "build_fair_pay_messages",
    "build_weather_messages",
    "build_pivot_messages",
    "build_atlas_prose_messages",
    "build_fair_pay_prose_messages",
    "build_weather_prose_messages",
    "build_pivot_prose_messages",
]
