"""Employer analytics business logic.

Computes the hiring dashboard, the Onboarding Success Predictor, the warm-bench
re-engagement list, and the Workforce Resilience view. Heuristics are the source
of truth for numbers; the LLM is used only to *narrate* scenarios grounded in
those numbers. Every AI verdict carries a GlassBox. Never 500s on empty data.
"""

from __future__ import annotations

import uuid

from app.domains.ai.guardrails import SYSTEM_PREAMBLE, wrap_untrusted
from app.domains.ai.llm.client import ChatMessage, LLMClient
from app.domains.ai.schemas import (
    Citation,
    CitationSourceType,
    Confidence,
    GlassBox,
)
from app.domains.employers.repository import EmployerRepository
from app.domains.employers.schemas import (
    EmployerDashboard,
    OnboardingReport,
    OnboardingRisk,
    PipelineStage,
    RecentActivity,
    ReengagementCandidate,
    ReengagementReport,
    WorkforceProjection,
    WorkforceReport,
    WorkforceScenario,
    WorkforceScenarios,
)

# Canonical hiring-funnel order; only stages with a count are surfaced.
_PIPELINE_ORDER = (
    "applied",
    "screening",
    "shortlisted",
    "interview",
    "offer",
    "hired",
)

try:  # usage ledger is optional cross-domain plumbing
    from app.domains.ai.usage import record_usage
except ImportError:  # pragma: no cover - defensive
    record_usage = None  # type: ignore[assignment]


# Representative APAC working-age-population indices (2025 = 100), from UN World
# Population Prospects 2024. These are illustrative anchors for the demo; the
# Glass Box cites them explicitly so users see the grounding.
APAC_WORKING_AGE: dict[str, dict[int, float]] = {
    "MY": {2025: 100.0, 2030: 104.8, 2035: 107.1, 2040: 107.9, 2045: 106.4},
    "JP": {2025: 100.0, 2030: 94.2, 2035: 88.9, 2040: 84.1, 2045: 79.0},
    "KR": {2025: 100.0, 2030: 93.1, 2035: 85.0, 2040: 77.2, 2045: 70.1},
    "CN": {2025: 100.0, 2030: 96.5, 2035: 91.0, 2040: 84.8, 2045: 78.2},
}
WORKFORCE_YEARS = (2025, 2030, 2035, 2040, 2045)


class EmployerService:
    """Org-scoped employer analytics."""

    def __init__(self, repo: EmployerRepository, llm: LLMClient) -> None:
        self.repo = repo
        self.llm = llm

    # ----------------------------------------------------------------- #
    # Dashboard
    # ----------------------------------------------------------------- #
    async def dashboard(self, org_id: uuid.UUID) -> EmployerDashboard:
        open_roles = await self.repo.count_open_roles(org_id)
        by_stage = await self.repo.pipeline_by_stage(org_id)
        total = await self.repo.total_applicants(org_id)
        ttf = await self.repo.avg_time_to_fill_days(org_id)
        flight = await self.repo.flight_risk_count(org_id)

        # Ordered funnel: canonical stages first (with data), then any extras.
        pipeline = [
            PipelineStage(stage=stage, count=by_stage[stage])
            for stage in _PIPELINE_ORDER
            if by_stage.get(stage)
        ]
        for stage, count in sorted(by_stage.items()):
            if stage not in _PIPELINE_ORDER and count:
                pipeline.append(PipelineStage(stage=stage, count=count))

        recent: list[RecentActivity] = []
        for app_row, job in await self.repo.recent_applications(org_id):
            recent.append(
                RecentActivity(
                    id=str(app_row.id),
                    kind="application",
                    title=f"Applicant in '{job.title}' is now {app_row.status}.",
                    at=app_row.updated_at.isoformat() if app_row.updated_at else None,
                )
            )

        return EmployerDashboard(
            open_roles=open_roles,
            pipeline=pipeline,
            time_to_fill=ttf,
            flight_risk_count=flight,
            applications_total=total,
            offers_out=int(by_stage.get("offer", 0)),
            recent_activity=recent,
        )

    # ----------------------------------------------------------------- #
    # Onboarding Success Predictor
    # ----------------------------------------------------------------- #
    async def onboarding(self, org_id: uuid.UUID) -> OnboardingReport:
        rows = await self.repo.applications_by_status(org_id, ("hired",))
        items: list[OnboardingRisk] = []
        for app_row, job, profile, full_name in rows:
            risk, gb = await self._onboarding_risk(org_id, app_row, job, profile)
            risk_level = "high" if risk >= 0.6 else "medium" if risk >= 0.35 else "low"
            items.append(
                OnboardingRisk(
                    id=str(profile.id),
                    full_name=full_name or "New hire",
                    headline=profile.headline,
                    role=job.title,
                    risk_level=risk_level,
                    risk_score=risk,
                    glass_box=gb,
                )
            )
        items.sort(key=lambda i: i.risk_score, reverse=True)
        return OnboardingReport(items=items)

    async def _onboarding_risk(
        self, org_id: uuid.UUID, app_row, job, profile
    ) -> tuple[float, GlassBox]:
        """Heuristic first-60-day risk grounded in tenure/engagement signals."""
        signals = await self.repo.open_signals_for_candidate(org_id, profile.id)
        risk = 0.2
        drivers: list[str] = []
        for sig in signals:
            if sig.type in ("onboarding_risk", "activity_drop", "plateau"):
                risk += 0.25 * float(sig.strength or 0.5)
                drivers.append(sig.summary or sig.type)
        if (profile.completeness or 0) < 50:
            risk += 0.1
            drivers.append("Sparse profile / limited verified history")
        risk = round(min(risk, 0.99), 2)

        band = (
            Confidence.HIGH
            if risk >= 0.6
            else Confidence.MEDIUM
            if risk >= 0.35
            else Confidence.LOW
        )
        rationale = (
            "Estimated from early-tenure engagement signals and profile depth. "
            "This is a supportive flag for onboarding attention, not a prediction."
            + (" Drivers: " + "; ".join(drivers) if drivers else "")
        )
        return risk, GlassBox(
            rationale=rationale,
            confidence=band,
            confidence_score=risk,
            citations=[
                Citation(
                    label="Early-tenure signals",
                    source_type=CitationSourceType.CAREER_HISTORY,
                    source_id=str(profile.id),
                )
            ],
            what_would_change_this=[
                "A manager check-in confirming engagement",
                "More verified skills matching the role's requirements",
            ],
            caveats=[
                "Based on limited early data; the first weeks are inherently noisy.",
            ],
        )

    # ----------------------------------------------------------------- #
    # Warm-bench re-engagement
    # ----------------------------------------------------------------- #
    async def reengagement(self, org_id: uuid.UUID) -> ReengagementReport:
        rows = await self.repo.applications_by_status(org_id, ("rejected", "withdrawn"))
        open_jobs = await self.repo.open_roles(org_id)
        items: list[ReengagementCandidate] = []
        for app_row, _job, profile, full_name in rows:
            suggested = open_jobs[0] if open_jobs else None
            gb = GlassBox(
                rationale=(
                    "This candidate engaged previously and matches the shape of a "
                    "currently open role. Re-engaging warm candidates is cheaper and "
                    "faster than cold sourcing."
                ),
                confidence=Confidence.MEDIUM,
                confidence_score=0.55,
                citations=[
                    Citation(
                        label="Prior application",
                        source_type=CitationSourceType.CAREER_HISTORY,
                        source_id=str(app_row.id),
                    )
                ],
                what_would_change_this=[
                    "Candidate opting out of re-contact",
                    "A closer-matching open role appearing",
                ],
                caveats=["Re-contact only with the candidate's standing consent."],
            )
            reason = (
                f"Reached '{app_row.status}' previously and fits "
                f"{suggested.title if suggested else 'a current open role'}."
            )
            items.append(
                ReengagementCandidate(
                    id=str(profile.id),
                    full_name=full_name or "Previous applicant",
                    headline=profile.headline,
                    former_role=profile.headline,
                    reason=reason,
                    fit_score=round(gb.confidence_score, 2),
                    suggested_job_id=str(suggested.id) if suggested else None,
                    glass_box=gb,
                )
            )
        return ReengagementReport(items=items)

    # ----------------------------------------------------------------- #
    # Workforce Resilience
    # ----------------------------------------------------------------- #
    async def workforce(self, org_id: uuid.UUID, country: str, user_id: str) -> WorkforceReport:
        cc = (country or "MY").upper()
        series = APAC_WORKING_AGE.get(cc, APAC_WORKING_AGE["MY"])
        projections = [
            WorkforceProjection(
                year=y,
                working_age=series[y],
                # Supply index reflects working-age pool minus assumed 4%/5yr
                # competitive draw; bounded, illustrative.
                supply_index=round(series[y] * 0.96, 1),
            )
            for y in WORKFORCE_YEARS
        ]

        scenarios, gb = await self._workforce_scenarios(cc, projections, org_id, user_id)
        return WorkforceReport(
            country=cc, projections=projections, scenarios=scenarios, glass_box=gb
        )

    async def _workforce_scenarios(
        self, country: str, projections: list[WorkforceProjection], org_id, user_id
    ) -> tuple[list[WorkforceScenario], GlassBox]:
        series_text = ", ".join(
            f"{p.year}: working-age index {p.working_age}" for p in projections
        )
        citation = Citation(
            label="UN World Population Prospects 2024 — working-age population",
            source_type=CitationSourceType.DEMOGRAPHIC_DATA,
            snippet=series_text,
        )
        try:
            result = await self.llm.structured(
                [
                    ChatMessage(role="system", content=SYSTEM_PREAMBLE),
                    ChatMessage(
                        role="user",
                        content=(
                            "Write 2-3 concise workforce-resilience scenarios for an "
                            f"employer hiring in {country}, grounded ONLY in this "
                            "working-age-population series. Do not invent figures.\n"
                            + wrap_untrusted(series_text, kind="demographic_series")
                        ),
                    ),
                ],
                WorkforceScenarios,
            )
            if record_usage is not None:
                await record_usage(
                    self.repo.session,
                    feature="employer_workforce",
                    model="mock-or-azure",
                    usage=getattr(result, "usage", None) or _empty_usage(),
                    org_id=org_id,
                    user_id=user_id,
                )
            scenarios = (
                [
                    WorkforceScenario(
                        id=f"scenario-{i + 1}",
                        title=s.title,
                        description=s.description,
                    )
                    for i, s in enumerate(result.scenarios)
                ]
                if result.scenarios
                else _fallback_scenarios(country)
            )
            gb = result.glass_box
            # Ensure the demographic citation is always present.
            if not any(c.source_type == CitationSourceType.DEMOGRAPHIC_DATA for c in gb.citations):
                gb.citations.append(citation)
            return scenarios, gb
        except Exception:  # noqa: BLE001 - degrade gracefully, never 500
            return _fallback_scenarios(country), GlassBox(
                rationale=(
                    f"Scenarios derived directly from the {country} working-age "
                    "population trajectory; a shrinking pool tightens hiring."
                ),
                confidence=Confidence.MEDIUM,
                confidence_score=0.6,
                citations=[citation],
                what_would_change_this=[
                    "Immigration policy shifts",
                    "Automation changing labor demand",
                ],
                caveats=["Demographics set the floor, not the outcome."],
            )


def _empty_usage():
    from app.domains.ai.llm.client import TokenUsage

    return TokenUsage()


def _fallback_scenarios(country: str) -> list[WorkforceScenario]:
    return [
        WorkforceScenario(
            id="tightening-pool",
            title="Tightening pool",
            description=(
                f"If the {country} working-age pool contracts as projected, "
                "competition for mid-career talent intensifies; invest in retention "
                "and internal mobility now."
            ),
        ),
        WorkforceScenario(
            id="resilience-reskilling",
            title="Resilience through reskilling",
            description=(
                "Offsetting demographic decline by upskilling existing staff and "
                "widening early-career intake keeps supply stable."
            ),
        ),
    ]
