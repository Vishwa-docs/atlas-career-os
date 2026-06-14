"""University Outcomes Studio business logic (org-scoped).

Computes outcome analytics from Outcome + Cohort, builds the student roster with
a readiness score, produces the Adaptive Readiness Profile and Future-State
Curriculum (LLM-narrated, heuristic-grounded), and manages internship listings.
Robust to sparse data; commits at the boundary for writes.
"""

from __future__ import annotations

import statistics
import uuid

from app.domains.ai.guardrails import SYSTEM_PREAMBLE, wrap_untrusted
from app.domains.ai.llm.client import ChatMessage, LLMClient
from app.domains.ai.schemas import (
    Citation,
    CitationSourceType,
    Confidence,
    GlassBox,
)
from app.domains.universities.models import Internship
from app.domains.universities.repository import UniversityRepository
from app.domains.universities.schemas import (
    CurriculumReport,
    FieldRate,
    InternshipCreate,
    InternshipRead,
    MarketSkill,
    OutcomesReport,
    ReadinessDimension,
    ReadinessProfile,
    StudentRoster,
    StudentRosterEntry,
    TrendPoint,
    UniversityDashboard,
)

try:
    from app.domains.ai.usage import record_usage
except ImportError:  # pragma: no cover
    record_usage = None  # type: ignore[assignment]

_EMPLOYED = ("employed", "entrepreneur")


def _employment_rate(statuses: list[str]) -> float:
    if not statuses:
        return 0.0
    employed = sum(1 for s in statuses if s in _EMPLOYED)
    return round(employed / len(statuses), 3)


def _median_int(values: list[int]) -> int | None:
    vals = [v for v in values if v is not None]
    return int(round(statistics.median(vals))) if vals else None


def _median_float(values: list[int]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(float(statistics.median(vals)), 1) if vals else None


class UniversityService:
    """Org-scoped Outcomes Studio."""

    def __init__(self, repo: UniversityRepository, llm: LLMClient) -> None:
        self.repo = repo
        self.llm = llm

    # ----------------------------- dashboard -------------------------- #
    async def dashboard(self, org_id: uuid.UUID) -> UniversityDashboard:
        cohorts = await self.repo.count_cohorts(org_id)
        grads = await self.repo.tracked_graduates(org_id)
        rows = await self.repo.outcomes(org_id)
        statuses = [o.status for o, _ in rows]
        return UniversityDashboard(
            cohorts=cohorts,
            tracked_graduates=grads,
            employment_rate=_employment_rate(statuses),
            median_salary=_median_int([o.salary_myr for o, _ in rows]),
            median_months_to_employ=_median_float([o.months_to_employment for o, _ in rows]),
        )

    # ----------------------------- outcomes --------------------------- #
    async def outcomes(
        self,
        org_id: uuid.UUID,
        cohort_id: uuid.UUID | None,
        year: int | None,
    ) -> OutcomesReport:
        rows = await self.repo.outcomes(org_id, cohort_id, year)
        statuses = [o.status for o, _ in rows]

        # By field (cohort faculty/program).
        by_field_acc: dict[str, list[str]] = {}
        for outcome, cohort in rows:
            field = cohort.faculty or cohort.program or "General"
            by_field_acc.setdefault(field, []).append(outcome.status)
        by_field = [
            FieldRate(field=f, rate=_employment_rate(s)) for f, s in sorted(by_field_acc.items())
        ]

        # Trend by graduation year.
        trend_acc: dict[int, list[str]] = {}
        for outcome, cohort in rows:
            trend_acc.setdefault(cohort.graduation_year, []).append(outcome.status)
        trend = [TrendPoint(year=y, rate=_employment_rate(s)) for y, s in sorted(trend_acc.items())]

        return OutcomesReport(
            employment_rate=_employment_rate(statuses),
            median_salary=_median_int([o.salary_myr for o, _ in rows]),
            median_months_to_employ=_median_float([o.months_to_employment for o, _ in rows]),
            by_field=by_field,
            trend=trend,
        )

    # ----------------------------- students --------------------------- #
    async def students(self, org_id: uuid.UUID) -> StudentRoster:
        rows = await self.repo.roster(org_id)
        items: list[StudentRosterEntry] = []
        for student, cohort, profile in rows:
            skills = await self.repo.candidate_skills(profile.id)
            score = self._readiness_score(profile, skills)
            items.append(
                StudentRosterEntry(
                    candidate_id=str(profile.id),
                    cohort_id=str(cohort.id),
                    student_ref=student.student_ref,
                    headline=profile.headline,
                    program=cohort.program,
                    graduation_year=cohort.graduation_year,
                    readiness_score=score,
                )
            )
        items.sort(key=lambda i: i.readiness_score, reverse=True)
        return StudentRoster(items=items)

    @staticmethod
    def _readiness_score(profile, skills) -> float:
        """Blend profile completeness, skill breadth, and mean proficiency."""
        completeness = (profile.completeness or 0) / 100.0
        breadth = min(len(skills) / 10.0, 1.0)
        prof = sum(cs.proficiency for cs, _ in skills) / len(skills) if skills else 0.0
        return round(min(0.4 * completeness + 0.3 * breadth + 0.3 * prof, 1.0), 2)

    async def readiness(
        self, org_id: uuid.UUID, candidate_id: uuid.UUID, user_id: str
    ) -> ReadinessProfile | None:
        row = await self.repo.student_in_org(org_id, candidate_id)
        if row is None:
            return None
        _student, cohort, profile = row
        skills = await self.repo.candidate_skills(candidate_id)
        events = await self.repo.candidate_events(candidate_id)
        base = self._readiness_score(profile, skills)

        skill_names = ", ".join(s.name for _, s in skills) or "none recorded"
        event_titles = ", ".join(e.title for e in events) or "none recorded"
        context = f"Program: {cohort.program}. Skills: {skill_names}. Experiences: {event_titles}."
        try:
            result = await self.llm.structured(
                [
                    ChatMessage(role="system", content=SYSTEM_PREAMBLE),
                    ChatMessage(
                        role="user",
                        content=(
                            "Produce an Adaptive Readiness Profile for this student "
                            "across dimensions (e.g. technical depth, communication, "
                            "industry exposure, adaptability). Ground every note in "
                            "the provided skills and experiences; do not invent any.\n"
                            + wrap_untrusted(context, kind="student_profile")
                        ),
                    ),
                ],
                ReadinessProfile,
            )
            if record_usage is not None:
                await record_usage(
                    self.repo.session,
                    feature="university_readiness",
                    model="mock-or-azure",
                    usage=getattr(result, "usage", None) or _empty_usage(),
                    org_id=org_id,
                    user_id=user_id,
                )
            result.candidate_id = str(candidate_id)
            result.score = base
            if not result.glass_box.citations:
                result.glass_box.citations.append(
                    Citation(
                        label="Student skills & career events",
                        source_type=CitationSourceType.CAREER_HISTORY,
                        source_id=str(candidate_id),
                    )
                )
            return result
        except Exception:  # noqa: BLE001 - degrade gracefully
            return self._heuristic_readiness(candidate_id, base, skills, events)

    def _heuristic_readiness(
        self, candidate_id: uuid.UUID, base: float, skills, events
    ) -> ReadinessProfile:
        breadth = min(len(skills) / 10.0, 1.0)
        exposure = min(len(events) / 5.0, 1.0)
        prof = sum(cs.proficiency for cs, _ in skills) / len(skills) if skills else 0.0
        dims = [
            ReadinessDimension(
                name="Technical depth",
                score=round(prof, 2),
                note="Mean proficiency across recorded skills.",
            ),
            ReadinessDimension(
                name="Skill breadth",
                score=round(breadth, 2),
                note=f"{len(skills)} skills recorded.",
            ),
            ReadinessDimension(
                name="Industry exposure",
                score=round(exposure, 2),
                note=f"{len(events)} career events recorded.",
            ),
        ]
        return ReadinessProfile(
            candidate_id=str(candidate_id),
            score=base,
            dimensions=dims,
            glass_box=GlassBox(
                rationale=(
                    "Readiness blends profile depth, skill breadth, and mean "
                    "proficiency from the student's recorded graph — a snapshot, "
                    "not a prediction."
                ),
                confidence=Confidence.MEDIUM,
                confidence_score=base,
                citations=[
                    Citation(
                        label="Student skills & career events",
                        source_type=CitationSourceType.CAREER_HISTORY,
                        source_id=str(candidate_id),
                    )
                ],
                what_would_change_this=[
                    "Verified skills or completed internships",
                    "More detailed project narratives",
                ],
                caveats=["Sparse student records widen the uncertainty."],
            ),
        )

    # --------------------------- curriculum --------------------------- #
    async def curriculum(self, org_id: uuid.UUID, user_id: str) -> CurriculumReport:
        cohorts = await self.repo.cohorts(org_id)
        program = cohorts[0].program if cohorts else "Program"
        covered = sorted(await self.repo.cohort_skill_names(org_id))
        demand_skills = await self.repo.top_demand_skills()
        market = [MarketSkill(skill=s.name, demand=round(s.demand_trend, 3)) for s in demand_skills]
        covered_lower = {c.lower() for c in covered}
        gaps = [s.name for s in demand_skills if s.name.lower() not in covered_lower]

        context = (
            f"Program: {program}. Covered skills: {', '.join(covered) or 'none'}. "
            f"Rising market skills: {', '.join(s.name for s in demand_skills) or 'none'}. "
            f"Apparent gaps: {', '.join(gaps) or 'none'}."
        )
        gb: GlassBox
        try:
            narrated = await self.llm.structured(
                [
                    ChatMessage(role="system", content=SYSTEM_PREAMBLE),
                    ChatMessage(
                        role="user",
                        content=(
                            "Explain, in plain language, how well this program's "
                            "covered skills meet rising market demand, citing the "
                            "skill lists. Do not invent skills.\n"
                            + wrap_untrusted(context, kind="curriculum_context")
                        ),
                    ),
                ],
                CurriculumReport,
            )
            if record_usage is not None:
                await record_usage(
                    self.repo.session,
                    feature="university_curriculum",
                    model="mock-or-azure",
                    usage=getattr(narrated, "usage", None) or _empty_usage(),
                    org_id=org_id,
                    user_id=user_id,
                )
            gb = narrated.glass_box
        except Exception:  # noqa: BLE001
            gb = GlassBox(
                rationale=(
                    f"Compared {program}'s covered skills against rising-demand "
                    "skills (Skill.demand_trend > 0). Gaps are demand skills not yet "
                    "evidenced in the cohort."
                ),
                confidence=Confidence.MEDIUM,
                confidence_score=0.6,
                citations=[],
                what_would_change_this=[
                    "Adding the gap skills to coursework",
                    "Updated labor-market demand signals",
                ],
                caveats=["Coverage is inferred from student-held skills, not syllabi."],
            )
        if not any(c.source_type == CitationSourceType.SKILL_TAXONOMY for c in gb.citations):
            gb.citations.append(
                Citation(
                    label="Skill demand trend (taxonomy)",
                    source_type=CitationSourceType.SKILL_TAXONOMY,
                    snippet=", ".join(s.name for s in demand_skills) or None,
                )
            )
        return CurriculumReport(
            program=program,
            market_skills=market,
            covered=covered,
            gaps=gaps,
            glass_box=gb,
        )

    # --------------------------- internships -------------------------- #
    async def list_internships(self, org_id: uuid.UUID) -> list[InternshipRead]:
        rows = await self.repo.list_internships(org_id)
        return [_internship_read(i) for i in rows]

    async def create_internship(
        self, org_id: uuid.UUID, payload: InternshipCreate
    ) -> InternshipRead:
        internship = Internship(
            org_id=org_id,
            title=payload.title,
            description=payload.description,
            skills_focus=payload.skills_focus,
            grows_into=payload.grows_into,
            location=payload.location,
            duration_months=payload.duration_months,
            stipend_myr=payload.stipend_myr,
            status=payload.status or "open",
        )
        await self.repo.add_internship(internship)
        await self.repo.session.commit()
        await self.repo.session.refresh(internship)
        return _internship_read(internship)


def _empty_usage():
    from app.domains.ai.llm.client import TokenUsage

    return TokenUsage()


def _internship_read(i: Internship) -> InternshipRead:
    return InternshipRead(
        id=str(i.id),
        org_id=str(i.org_id),
        title=i.title,
        description=i.description,
        skills_focus=list(i.skills_focus or []),
        grows_into=list(i.grows_into or []),
        location=i.location,
        duration_months=i.duration_months,
        stipend_myr=i.stipend_myr,
        status=i.status,
    )
