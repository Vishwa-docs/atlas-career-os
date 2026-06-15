"""Business logic for the candidate Navigator.

Owns transaction boundaries (``await session.commit()``), enforces per-object
authorization (BOLA defence), and orchestrates the LLM for resume parsing and
profile embeddings. Raises semantic exceptions; the router stays thin.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConsentRequiredError, ForbiddenError, NotFoundError
from app.domains.ai.guardrails import SYSTEM_PREAMBLE, wrap_untrusted
from app.domains.ai.llm.client import ChatMessage
from app.domains.ai.llm.factory import get_llm
from app.domains.candidates.models import CandidateProfile, CandidateSkill, CareerEvent
from app.domains.candidates.repository import CandidateRepository
from app.domains.candidates.schemas import (
    CandidateDashboard,
    CandidateMe,
    CandidateProfileRead,
    CandidateProfileUpdate,
    CandidatePublic,
    CandidateSkillRead,
    CareerEventCreate,
    CareerEventRead,
    CareerEventUpdate,
    DashboardStat,
    MarketSnapshot,
    Nudge,
    RecentMatch,
    ResumeParse,
    SkillsReplace,
)

# Optional cross-domain usage ledger; degrade gracefully if absent.
try:  # pragma: no cover - defensive import
    from app.domains.ai.usage import record_usage
except ImportError:  # pragma: no cover
    record_usage = None  # type: ignore[assignment]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def build_profile_text(profile: CandidateProfile, skills: list[str]) -> str:
    """Compose the text we embed for matching: headline + summary + aspirations + skills."""
    parts: list[str] = []
    if profile.headline:
        parts.append(profile.headline)
    if profile.summary:
        parts.append(profile.summary)
    if profile.aspirations:
        parts.append(profile.aspirations)
    if skills:
        parts.append("Skills: " + ", ".join(skills))
    return "\n".join(parts).strip() or "Candidate profile"


def _completeness(profile: CandidateProfile, n_events: int, n_skills: int) -> int:
    """Percentage of key sections filled (0–100)."""
    sections = [
        bool(profile.headline),
        bool(profile.summary),
        bool(profile.location),
        bool(profile.aspirations),
        profile.target_occupation_id is not None,
        profile.years_experience > 0,
        n_events > 0,
        n_skills > 0,
    ]
    return round(100 * sum(1 for s in sections if s) / len(sections))


def _skill_read(cskill: CandidateSkill, name: str | None, slug: str | None) -> CandidateSkillRead:
    return CandidateSkillRead(
        id=cskill.id,
        skill_id=cskill.skill_id,
        name=name,
        slug=slug,
        proficiency=cskill.proficiency,
        evidence_type=cskill.evidence_type,
        confidence=cskill.confidence,
        years=cskill.years,
    )


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


class CandidateService:
    """Coordinates repository access, the LLM, and authorization."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CandidateRepository(session)

    # ----------------------------- profile -------------------------------- #
    async def _get_or_create_profile(self, user_id: uuid.UUID) -> CandidateProfile:
        profile = await self.repo.get_profile_by_user(user_id)
        if profile is None:
            profile = CandidateProfile(user_id=user_id)
            self.repo.add_profile(profile)
            await self.session.commit()
            await self.session.refresh(profile)
        return profile

    async def get_me(self, user_id: str) -> CandidateMe:
        """Return the full profile, timeline, skills, completeness. Auto-creates profile."""
        uid = uuid.UUID(user_id)
        profile = await self._get_or_create_profile(uid)
        events = await self.repo.list_career_events(profile.id)
        skills = await self.repo.list_candidate_skills(profile.id)
        completeness = _completeness(profile, len(events), len(skills))
        if profile.completeness != completeness:
            profile.completeness = completeness
            await self.session.commit()
        return CandidateMe(
            profile=CandidateProfileRead.model_validate(profile),
            career_events=[CareerEventRead.model_validate(e) for e in events],
            skills=[_skill_read(cs, sk.name, sk.slug) for cs, sk in skills],
            completeness=completeness,
        )

    async def update_me(self, user_id: str, payload: CandidateProfileUpdate) -> CandidateMe:
        """Patch profile fields, recompute completeness, refresh the embedding."""
        uid = uuid.UUID(user_id)
        profile = await self._get_or_create_profile(uid)

        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(profile, field, value)

        events = await self.repo.list_career_events(profile.id)
        skills = await self.repo.list_candidate_skills(profile.id)
        profile.completeness = _completeness(profile, len(events), len(skills))

        # Recompute the semantic embedding from the textual profile + skills.
        skill_names = [sk.name for _, sk in skills]
        try:
            text = build_profile_text(profile, skill_names)
            vectors = await get_llm().embed([text])
            if vectors:
                profile.embedding = vectors[0]
        except Exception:  # pragma: no cover - embedding is best-effort
            pass

        await self.session.commit()
        await self.session.refresh(profile)
        return CandidateMe(
            profile=CandidateProfileRead.model_validate(profile),
            career_events=[CareerEventRead.model_validate(e) for e in events],
            skills=[_skill_read(cs, sk.name, sk.slug) for cs, sk in skills],
            completeness=profile.completeness,
        )

    # --------------------------- resume parse ----------------------------- #
    async def parse_resume(self, user_id: str, text: str) -> ResumeParse:
        """LLM-extract a structured resume (preview only — not committed to the graph)."""
        if not text or not text.strip():
            raise NotFoundError("No resume text provided.")
        uid = uuid.UUID(user_id)
        await self._get_or_create_profile(uid)

        llm = get_llm()
        messages = [
            ChatMessage(role="system", content=SYSTEM_PREAMBLE),
            ChatMessage(
                role="user",
                content=(
                    "Extract a structured career profile from the resume below. "
                    "Return the candidate's name, a headline, a short summary, "
                    "their work experiences, education, and skills. For each "
                    "inference include a confidence in [0,1], and fill the glass_box "
                    "explaining your reasoning, evidence, and caveats.\n\n"
                    + wrap_untrusted(text, kind="resume")
                ),
            ),
        ]
        parsed = await llm.structured(messages, ResumeParse)

        if record_usage is not None:
            usage = getattr(parsed, "usage", None)
            if usage is None:
                from app.domains.ai.llm.client import TokenUsage

                usage = TokenUsage(prompt_tokens=len(text) // 4, completion_tokens=128)
            try:
                await record_usage(
                    self.session,
                    feature="resume_parse",
                    model="mock-or-azure",
                    usage=usage,
                    org_id=None,
                    user_id=uid,
                )
                await self.session.commit()
            except Exception:  # pragma: no cover - ledger is best-effort
                await self.session.rollback()
        return parsed

    # --------------------------- career events ---------------------------- #
    async def create_career_event(
        self, user_id: str, payload: CareerEventCreate
    ) -> CareerEventRead:
        profile = await self._get_or_create_profile(uuid.UUID(user_id))
        event = CareerEvent(candidate_id=profile.id, **payload.model_dump())
        self.repo.add_career_event(event)
        await self.session.commit()
        await self.session.refresh(event)
        return CareerEventRead.model_validate(event)

    async def update_career_event(
        self, user_id: str, event_id: str, payload: CareerEventUpdate
    ) -> CareerEventRead:
        profile = await self._get_or_create_profile(uuid.UUID(user_id))
        event = await self._owned_event(event_id, profile.id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(event, field, value)
        await self.session.commit()
        await self.session.refresh(event)
        return CareerEventRead.model_validate(event)

    async def delete_career_event(self, user_id: str, event_id: str) -> None:
        profile = await self._get_or_create_profile(uuid.UUID(user_id))
        event = await self._owned_event(event_id, profile.id)
        await self.repo.delete_career_event(event)
        await self.session.commit()

    async def _owned_event(self, event_id: str, candidate_id: uuid.UUID) -> CareerEvent:
        event = await self.repo.get_career_event(uuid.UUID(event_id))
        if event is None:
            raise NotFoundError("Career event not found.")
        if event.candidate_id != candidate_id:
            raise ForbiddenError("You do not own this career event.")
        return event

    # ------------------------------ skills -------------------------------- #
    async def get_skills(self, user_id: str) -> list[CandidateSkillRead]:
        profile = await self._get_or_create_profile(uuid.UUID(user_id))
        skills = await self.repo.list_candidate_skills(profile.id)
        return [_skill_read(cs, sk.name, sk.slug) for cs, sk in skills]

    async def replace_skills(
        self, user_id: str, payload: SkillsReplace
    ) -> list[CandidateSkillRead]:
        """Replace or merge the candidate's skill set, resolving each to the taxonomy."""
        profile = await self._get_or_create_profile(uuid.UUID(user_id))
        if not payload.merge:
            await self.repo.clear_candidate_skills(profile.id)

        for item in payload.skills:
            skill = await self.repo.resolve_or_create_skill(item.name)
            existing = await self.repo.get_candidate_skill(profile.id, skill.id)
            if existing is not None:
                existing.proficiency = item.proficiency
                existing.evidence_type = item.evidence_type
                existing.confidence = item.confidence
                existing.years = item.years
            else:
                self.repo.add_candidate_skill(
                    CandidateSkill(
                        candidate_id=profile.id,
                        skill_id=skill.id,
                        proficiency=item.proficiency,
                        evidence_type=item.evidence_type,
                        confidence=item.confidence,
                        years=item.years,
                    )
                )
        await self.session.commit()
        return await self.get_skills(user_id)

    # ----------------------------- dashboard ------------------------------ #
    async def get_dashboard(self, user_id: str) -> CandidateDashboard:
        """Assemble the candidate home dashboard. Robust to empty/absent data.

        Fast by design: stats and the market snapshot are pure heuristics and
        ``recent_matches`` is a cheap pgvector cosine ranking — no LLM call.
        """
        uid = uuid.UUID(user_id)
        profile = await self._get_or_create_profile(uid)
        n_events = await self.repo.count_career_events(profile.id)
        n_skills = await self.repo.count_skills(profile.id)
        completeness = _completeness(profile, n_events, n_skills)

        applications = await self._safe_application_count(profile.id)
        matches = await self._safe_match_count(profile.id)
        recent_matches = await self._recent_matches(profile)
        market_snapshot, percentile = await self._safe_market(profile)

        stats = [
            DashboardStat(label="Applications", value=applications, tone="brand"),
            DashboardStat(
                label="Job matches",
                value=max(matches, len(recent_matches)),
                hint="Roles aligned to your trajectory",
            ),
            DashboardStat(
                label="Profile completeness",
                value=f"{completeness}%",
                tone="success" if completeness >= 80 else "warning",
            ),
            DashboardStat(
                label="Market percentile",
                value=f"{percentile}%" if percentile is not None else "—",
                hint=None if percentile is not None else "Set a target occupation",
            ),
        ]

        nudges = self._nudges(profile, n_events, n_skills, completeness)
        return CandidateDashboard(
            stats=stats,
            recent_matches=recent_matches,
            nudges=nudges,
            market_snapshot=market_snapshot,
        )

    async def _recent_matches(self, profile: CandidateProfile) -> list[RecentMatch]:
        """Top ~3 open jobs by pgvector cosine distance to the candidate. No LLM."""
        embedding = getattr(profile, "embedding", None)
        if embedding is None:
            return []
        try:
            rows = await self.repo.top_jobs_by_embedding(embedding, limit=3)
        except Exception:  # pragma: no cover - vector op best-effort
            return []
        out: list[RecentMatch] = []
        for job, org_name in rows:
            # cosine_distance ∈ [0, 2]; map to a 0..1 similarity score.
            score = await self._job_similarity(profile, job)
            out.append(
                RecentMatch(
                    job_id=str(job.id),
                    title=job.title,
                    company=org_name or "Confidential",
                    location=job.location,
                    score=score,
                )
            )
        return out

    async def _job_similarity(self, profile: CandidateProfile, job) -> float:
        """0..1 cosine similarity between the candidate and a job embedding."""
        from app.domains.matching.service import cosine

        sim = cosine(getattr(profile, "embedding", None), getattr(job, "embedding", None))
        return round(sim if sim is not None else 0.5, 4)

    def _nudges(
        self, profile: CandidateProfile, n_events: int, n_skills: int, completeness: int
    ) -> list[Nudge]:
        nudges: list[Nudge] = []
        if not profile.headline or not profile.summary:
            nudges.append(
                Nudge(
                    id="profile",
                    title="Complete your headline",
                    body="A headline and summary help employers and the matcher understand you.",
                    tone="info",
                    cta_label="Edit profile",
                    cta_to="/app/profile",
                )
            )
        if n_skills < 5:
            nudges.append(
                Nudge(
                    id="skills",
                    title="Add more skills",
                    body="List at least 5 skills so we can map you against real roles.",
                    tone="warning",
                    cta_label="Add skills",
                    cta_to="/app/profile",
                )
            )
        if n_events == 0:
            nudges.append(
                Nudge(
                    id="timeline",
                    title="Map your career timeline",
                    body="Add roles, study, and projects to unlock trajectory insights.",
                    tone="info",
                    cta_label="Add timeline",
                    cta_to="/app/profile",
                )
            )
        if completeness >= 80 and not nudges:
            nudges.append(
                Nudge(
                    id="match-ready",
                    title="You're match-ready",
                    body="Your profile is strong — explore the Trajectory Atlas next.",
                    tone="success",
                    cta_label="Open Atlas",
                    cta_to="/app/atlas",
                )
            )
        return nudges

    async def _safe_application_count(self, candidate_id: uuid.UUID) -> int:
        try:
            from sqlalchemy import func, select

            from app.domains.applications.models import Application  # type: ignore

            stmt = select(func.count(Application.id)).where(
                Application.candidate_id == candidate_id
            )
            return int((await self.session.execute(stmt)).scalar_one() or 0)
        except Exception:  # pragma: no cover - cross-domain best-effort
            return 0

    async def _safe_match_count(self, candidate_id: uuid.UUID) -> int:
        try:
            from sqlalchemy import func, select

            from app.domains.matching.models import MatchResult  # type: ignore

            stmt = select(func.count(MatchResult.id)).where(
                MatchResult.candidate_id == candidate_id
            )
            return int((await self.session.execute(stmt)).scalar_one() or 0)
        except Exception:  # pragma: no cover
            return 0

    async def _safe_market(
        self, profile: CandidateProfile
    ) -> tuple[MarketSnapshot | None, int | None]:
        """Derive the hero market snapshot from the target/current occupation.

        outlook/demand_index/salary_drift come from the occupation's skills'
        demand_trend; summary is anchored on the median salary. Cheap, no LLM.
        Returns ``(snapshot, percentile)``; snapshot is ``None`` when there is no
        occupation to anchor on so the frontend shows its empty hint.
        """
        occ_id = profile.target_occupation_id or profile.current_occupation_id
        if occ_id is None:
            return None, None
        try:
            occ = await self.repo.get_occupation(occ_id)
            trends = await self.repo.occupation_skill_demand(occ_id)
        except Exception:  # pragma: no cover - taxonomy best-effort
            return None, None
        if occ is None:
            return None, None

        median = occ.median_salary_myr
        # Mean demand_trend ∈ roughly [-0.5, 0.8]; map to a 0..100 demand index
        # centred on 50 with a damped slope so strong signals stay believable.
        mean_trend = sum(trends) / len(trends) if trends else 0.0
        demand_index = round(max(0.0, min(100.0, 50.0 + mean_trend * 50.0)), 1)
        # Salary drift is an annualised proxy: demand intensity scaled to a
        # realistic single-digit-ish percentage.
        salary_drift_pct = round(mean_trend * 12.0, 1)
        if demand_index >= 60:
            outlook = "sunny"
        elif demand_index >= 45:
            outlook = "cloudy"
        else:
            outlook = "stormy"

        trend_word = "rising" if mean_trend > 0 else "softening" if mean_trend < 0 else "steady"
        if median:
            summary = (
                f"{occ.title} pays a median ~RM{median:,}/month in Malaysia; "
                f"skill demand is {trend_word}."
            )
        else:
            summary = f"Skill demand for {occ.title} is {trend_word}."

        snapshot = MarketSnapshot(
            outlook=outlook,
            demand_index=demand_index,
            salary_drift_pct=salary_drift_pct,
            summary=summary,
        )
        return snapshot, None

    # ------------------------- consent-gated view ------------------------- #
    async def get_public_candidate(
        self,
        candidate_id: str,
        *,
        viewer_org_id: str | None,
        is_platform_admin: bool,
    ) -> CandidatePublic:
        """Employer/university view, gated by an active 'profile' consent grant."""
        cid = uuid.UUID(candidate_id)
        profile = await self.repo.get_profile_by_id(cid)
        if profile is None:
            raise NotFoundError("Candidate not found.")

        scopes: set[str] = set()
        if is_platform_admin:
            scopes = {"profile", "career_history", "skills", "salary", "contact", "trajectory"}
        else:
            if not viewer_org_id:
                raise ConsentRequiredError("This profile requires an active consent grant.")
            org_uuid = uuid.UUID(viewer_org_id)
            grant = await self.repo.active_grant(cid, org_uuid, "profile")
            if grant is None:
                raise ConsentRequiredError("This profile requires an active consent grant.")
            scopes = await self.repo.list_active_scopes(cid, org_uuid)

        public = CandidatePublic(
            id=profile.id,
            headline=profile.headline,
            summary=profile.summary,
            location=profile.location if "contact" in scopes else None,
            country=profile.country,
            years_experience=profile.years_experience,
            open_to_work=profile.open_to_work,
            target_occupation_id=profile.target_occupation_id if "trajectory" in scopes else None,
            current_occupation_id=profile.current_occupation_id,
            scopes=sorted(scopes),
        )
        if "skills" in scopes:
            skills = await self.repo.list_candidate_skills(profile.id)
            public.skills = [_skill_read(cs, sk.name, sk.slug) for cs, sk in skills]
        if "career_history" in scopes:
            events = await self.repo.list_career_events(profile.id)
            public.career_events = [CareerEventRead.model_validate(e) for e in events]
        return public
