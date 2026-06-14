"""Demo seed script — populate a rich, realistic, LEGAL dataset.

Run with::

    python -m app.scripts.seed            # seed (skip nothing)
    python -m app.scripts.seed --if-empty # skip entirely if any users exist

The data is a blend of open-data anchors (O*NET/ESCO skill names, ISCO-08 codes,
OpenDOSM-style median salaries) and *synthetic* people/orgs/jobs — no real
personal data is used. Everything every screen needs comes alive: a connected
career graph, four demo logins, candidate timelines with embeddings, jobs,
applications across every status, cohorts/outcomes, signals, notifications, and
consent grants so the employer talent-search demo works end to end.

It writes via the ORM models directly (no service layer) and computes embeddings
with ``get_llm().embed`` in reasonable batches. Idempotent under ``--if-empty``.
"""

from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select

from app.core.db import SessionFactory, engine
from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.registry import import_all_models

# --- ORM models (import directly; we own none of these, only read/instantiate) ---
from app.domains.admin.models import AuditLog
from app.domains.ai.llm.factory import get_llm
from app.domains.ai.models import Embedding, LlmUsage
from app.domains.applications.models import (
    APPLICATION_STATUSES,
    Application,
    ApplicationEvent,
)
from app.domains.candidates.models import (
    CandidateProfile,
    CandidateSkill,
    CareerEvent,
)
from app.domains.consent.models import ConsentGrant
from app.domains.credentials.models import Credential
from app.domains.jobs.models import Job
from app.domains.notifications.models import Notification
from app.domains.organizations.models import Membership, Organization
from app.domains.signals.models import Signal
from app.domains.taxonomy.models import (
    Occupation,
    OccupationSkill,
    OccupationTransition,
    Skill,
)
from app.domains.universities.models import Cohort, CohortStudent, Internship, Outcome
from app.domains.users.models import User

configure_logging()
log = get_logger(__name__)

DEMO_PASSWORD = "demo1234"
EMBED_BATCH = 32
random.seed(42)  # reproducible demo data


def _slug(name: str) -> str:
    return (
        name.lower()
        .replace("&", "and")
        .replace("/", "-")
        .replace("(", "")
        .replace(")", "")
        .replace(".", "")
        .replace(",", "")
        .replace("'", "")
        .replace(" ", "-")
    )


def _dt(year: int, month: int = 1, day: int = 1) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


# --------------------------------------------------------------------------- #
# 1) Taxonomy
# --------------------------------------------------------------------------- #
SKILLS: list[tuple[str, str, float]] = [
    # (name, category, demand_trend)
    ("Python", "programming", 0.7),
    ("JavaScript", "programming", 0.45),
    ("TypeScript", "programming", 0.6),
    ("Java", "programming", 0.1),
    ("Go", "programming", 0.55),
    ("SQL", "data", 0.4),
    ("React", "frontend", 0.5),
    ("Node.js", "backend", 0.4),
    ("FastAPI", "backend", 0.65),
    ("Django", "backend", 0.2),
    ("Kubernetes", "devops", 0.7),
    ("Docker", "devops", 0.5),
    ("AWS", "cloud", 0.6),
    ("Azure", "cloud", 0.55),
    ("CI/CD", "devops", 0.45),
    ("Machine Learning", "data-science", 0.8),
    ("Deep Learning", "data-science", 0.75),
    ("Data Visualization", "data", 0.35),
    ("Power BI", "data", 0.3),
    ("Tableau", "data", 0.25),
    ("ETL", "data", 0.3),
    ("Statistics", "data-science", 0.3),
    ("NLP", "data-science", 0.7),
    ("Product Management", "business", 0.4),
    ("Agile/Scrum", "business", 0.2),
    ("Stakeholder Management", "business", 0.25),
    ("UX Design", "design", 0.4),
    ("UI Design", "design", 0.35),
    ("Figma", "design", 0.4),
    ("Digital Marketing", "marketing", 0.35),
    ("SEO", "marketing", 0.2),
    ("Content Strategy", "marketing", 0.25),
    ("Financial Analysis", "finance", 0.15),
    ("Accounting", "finance", 0.05),
    ("Audit", "finance", -0.05),
    ("Risk Management", "finance", 0.2),
    ("Patient Care", "healthcare", 0.3),
    ("Clinical Assessment", "healthcare", 0.25),
    ("Project Management", "business", 0.3),
    ("Communication", "soft-skills", 0.2),
    ("Cybersecurity", "security", 0.78),
    ("Excel", "data", -0.1),
]

# (title, isco, masco, family, typical_education, median_salary_myr)
OCCUPATIONS: list[tuple[str, str, str, str, str, int]] = [
    ("Software Engineer", "2512", "2512-01", "ICT", "Bachelor", 7000),
    ("Senior Software Engineer", "2512", "2512-02", "ICT", "Bachelor", 11000),
    ("Frontend Developer", "2513", "2513-01", "ICT", "Bachelor", 6500),
    ("Backend Developer", "2512", "2512-03", "ICT", "Bachelor", 7000),
    ("DevOps Engineer", "2519", "2519-01", "ICT", "Bachelor", 9000),
    ("Data Analyst", "2511", "2511-01", "ICT", "Bachelor", 5500),
    ("Senior Data Analyst", "2511", "2511-02", "ICT", "Bachelor", 8500),
    ("Data Scientist", "2511", "2511-03", "ICT", "Master", 9500),
    ("Machine Learning Engineer", "2512", "2512-04", "ICT", "Master", 12000),
    ("Data Engineer", "2511", "2511-04", "ICT", "Bachelor", 9000),
    ("Product Manager", "1330", "1330-01", "Management", "Bachelor", 11000),
    ("Product Designer", "2166", "2166-01", "Design", "Bachelor", 7000),
    ("UX Designer", "2166", "2166-02", "Design", "Bachelor", 6500),
    ("Engineering Manager", "1330", "1330-02", "Management", "Bachelor", 16000),
    ("Marketing Executive", "2431", "2431-01", "Marketing", "Bachelor", 4500),
    ("Marketing Manager", "1221", "1221-01", "Marketing", "Bachelor", 9000),
    ("Digital Marketing Specialist", "2431", "2431-02", "Marketing", "Bachelor", 5500),
    ("Accountant", "2411", "2411-01", "Finance", "Bachelor", 5000),
    ("Senior Accountant", "2411", "2411-02", "Finance", "Bachelor", 7500),
    ("Financial Analyst", "2413", "2413-01", "Finance", "Bachelor", 6000),
    ("Auditor", "2411", "2411-03", "Finance", "Bachelor", 5500),
    ("Registered Nurse", "2221", "2221-01", "Healthcare", "Diploma", 4000),
    ("Project Manager", "1219", "1219-01", "Management", "Bachelor", 9500),
    ("Business Analyst", "2421", "2421-01", "Business", "Bachelor", 6500),
    ("Cybersecurity Analyst", "2529", "2529-01", "ICT", "Bachelor", 8000),
]

# Realistic next-move edges by title.
TRANSITIONS: list[tuple[str, str, float, int, float]] = [
    # (from, to, weight, median_months, salary_delta_pct)
    ("Software Engineer", "Senior Software Engineer", 0.55, 30, 0.45),
    ("Software Engineer", "Backend Developer", 0.2, 12, 0.0),
    ("Software Engineer", "DevOps Engineer", 0.15, 18, 0.28),
    ("Frontend Developer", "Software Engineer", 0.3, 18, 0.1),
    ("Backend Developer", "Senior Software Engineer", 0.4, 28, 0.55),
    ("Backend Developer", "Data Engineer", 0.2, 20, 0.3),
    ("Senior Software Engineer", "Engineering Manager", 0.35, 36, 0.45),
    ("Senior Software Engineer", "Machine Learning Engineer", 0.15, 24, 0.1),
    ("DevOps Engineer", "Engineering Manager", 0.2, 36, 0.55),
    ("Data Analyst", "Senior Data Analyst", 0.5, 24, 0.55),
    ("Data Analyst", "Data Scientist", 0.3, 30, 0.72),
    ("Data Analyst", "Business Analyst", 0.15, 18, 0.18),
    ("Senior Data Analyst", "Data Scientist", 0.4, 24, 0.12),
    ("Senior Data Analyst", "Product Manager", 0.15, 30, 0.3),
    ("Data Scientist", "Machine Learning Engineer", 0.4, 24, 0.26),
    ("Data Engineer", "Machine Learning Engineer", 0.25, 30, 0.33),
    ("Marketing Executive", "Digital Marketing Specialist", 0.35, 18, 0.22),
    ("Marketing Executive", "Marketing Manager", 0.3, 42, 1.0),
    ("Digital Marketing Specialist", "Marketing Manager", 0.4, 36, 0.64),
    ("Accountant", "Senior Accountant", 0.55, 30, 0.5),
    ("Accountant", "Financial Analyst", 0.25, 24, 0.2),
    ("Senior Accountant", "Financial Analyst", 0.2, 24, -0.2),
    ("Auditor", "Senior Accountant", 0.3, 30, 0.36),
    ("Financial Analyst", "Business Analyst", 0.2, 24, 0.08),
    ("Business Analyst", "Product Manager", 0.35, 36, 0.69),
    ("Product Designer", "Product Manager", 0.25, 36, 0.57),
    ("UX Designer", "Product Designer", 0.4, 24, 0.08),
    ("Project Manager", "Product Manager", 0.25, 30, 0.16),
    ("Cybersecurity Analyst", "DevOps Engineer", 0.15, 24, 0.12),
]

# occupation title -> list of (skill_name, importance, level, essential)
OCC_SKILLS: dict[str, list[tuple[str, float, float, bool]]] = {
    "Software Engineer": [
        ("Python", 0.8, 0.7, True),
        ("JavaScript", 0.6, 0.6, False),
        ("SQL", 0.6, 0.6, True),
        ("Docker", 0.5, 0.5, False),
        ("Communication", 0.5, 0.6, True),
    ],
    "Senior Software Engineer": [
        ("Python", 0.9, 0.85, True),
        ("Kubernetes", 0.6, 0.6, False),
        ("AWS", 0.6, 0.6, False),
        ("CI/CD", 0.6, 0.7, True),
        ("Stakeholder Management", 0.5, 0.6, False),
    ],
    "Frontend Developer": [
        ("JavaScript", 0.9, 0.8, True),
        ("TypeScript", 0.7, 0.6, True),
        ("React", 0.85, 0.75, True),
        ("UI Design", 0.5, 0.5, False),
    ],
    "Backend Developer": [
        ("Python", 0.8, 0.75, True),
        ("FastAPI", 0.6, 0.6, False),
        ("Node.js", 0.5, 0.5, False),
        ("SQL", 0.7, 0.7, True),
        ("Docker", 0.6, 0.6, False),
    ],
    "DevOps Engineer": [
        ("Kubernetes", 0.85, 0.8, True),
        ("Docker", 0.8, 0.8, True),
        ("AWS", 0.7, 0.7, True),
        ("CI/CD", 0.8, 0.8, True),
        ("Go", 0.4, 0.4, False),
    ],
    "Data Analyst": [
        ("SQL", 0.9, 0.75, True),
        ("Excel", 0.6, 0.7, True),
        ("Power BI", 0.6, 0.6, False),
        ("Data Visualization", 0.7, 0.6, True),
        ("Statistics", 0.6, 0.5, False),
    ],
    "Senior Data Analyst": [
        ("SQL", 0.9, 0.85, True),
        ("Python", 0.7, 0.6, True),
        ("Tableau", 0.6, 0.7, False),
        ("Statistics", 0.7, 0.7, True),
        ("Stakeholder Management", 0.6, 0.6, True),
    ],
    "Data Scientist": [
        ("Python", 0.9, 0.8, True),
        ("Machine Learning", 0.85, 0.75, True),
        ("Statistics", 0.8, 0.75, True),
        ("SQL", 0.7, 0.7, True),
        ("NLP", 0.5, 0.5, False),
    ],
    "Machine Learning Engineer": [
        ("Python", 0.9, 0.85, True),
        ("Machine Learning", 0.9, 0.85, True),
        ("Deep Learning", 0.8, 0.75, True),
        ("Docker", 0.6, 0.6, False),
        ("AWS", 0.6, 0.6, False),
    ],
    "Data Engineer": [
        ("Python", 0.8, 0.75, True),
        ("SQL", 0.85, 0.8, True),
        ("ETL", 0.8, 0.75, True),
        ("AWS", 0.6, 0.6, False),
        ("Docker", 0.5, 0.5, False),
    ],
    "Product Manager": [
        ("Product Management", 0.9, 0.8, True),
        ("Agile/Scrum", 0.7, 0.7, True),
        ("Stakeholder Management", 0.8, 0.75, True),
        ("SQL", 0.4, 0.4, False),
        ("Communication", 0.8, 0.8, True),
    ],
    "Product Designer": [
        ("UX Design", 0.8, 0.75, True),
        ("UI Design", 0.8, 0.75, True),
        ("Figma", 0.8, 0.8, True),
        ("Communication", 0.6, 0.6, True),
    ],
    "UX Designer": [
        ("UX Design", 0.9, 0.8, True),
        ("Figma", 0.7, 0.7, True),
        ("UI Design", 0.6, 0.6, False),
        ("Communication", 0.6, 0.6, True),
    ],
    "Engineering Manager": [
        ("Stakeholder Management", 0.9, 0.85, True),
        ("Agile/Scrum", 0.7, 0.7, True),
        ("Communication", 0.9, 0.85, True),
        ("Project Management", 0.7, 0.7, True),
        ("Python", 0.4, 0.6, False),
    ],
    "Marketing Executive": [
        ("Digital Marketing", 0.7, 0.6, True),
        ("Content Strategy", 0.6, 0.5, True),
        ("Communication", 0.7, 0.7, True),
        ("SEO", 0.5, 0.4, False),
    ],
    "Marketing Manager": [
        ("Digital Marketing", 0.8, 0.75, True),
        ("Stakeholder Management", 0.7, 0.7, True),
        ("Content Strategy", 0.7, 0.7, True),
        ("Communication", 0.8, 0.8, True),
    ],
    "Digital Marketing Specialist": [
        ("Digital Marketing", 0.85, 0.75, True),
        ("SEO", 0.7, 0.65, True),
        ("Content Strategy", 0.6, 0.6, True),
        ("Data Visualization", 0.4, 0.4, False),
    ],
    "Accountant": [
        ("Accounting", 0.9, 0.8, True),
        ("Excel", 0.8, 0.8, True),
        ("Financial Analysis", 0.5, 0.5, False),
        ("Communication", 0.5, 0.5, True),
    ],
    "Senior Accountant": [
        ("Accounting", 0.9, 0.85, True),
        ("Financial Analysis", 0.7, 0.7, True),
        ("Audit", 0.5, 0.5, False),
        ("Excel", 0.8, 0.8, True),
    ],
    "Financial Analyst": [
        ("Financial Analysis", 0.9, 0.8, True),
        ("Excel", 0.8, 0.8, True),
        ("SQL", 0.5, 0.5, False),
        ("Risk Management", 0.5, 0.5, False),
    ],
    "Auditor": [
        ("Audit", 0.9, 0.8, True),
        ("Accounting", 0.8, 0.75, True),
        ("Risk Management", 0.6, 0.6, True),
        ("Excel", 0.7, 0.7, True),
    ],
    "Registered Nurse": [
        ("Patient Care", 0.95, 0.85, True),
        ("Clinical Assessment", 0.8, 0.75, True),
        ("Communication", 0.8, 0.8, True),
    ],
    "Project Manager": [
        ("Project Management", 0.9, 0.85, True),
        ("Agile/Scrum", 0.7, 0.7, True),
        ("Stakeholder Management", 0.8, 0.8, True),
        ("Communication", 0.8, 0.8, True),
    ],
    "Business Analyst": [
        ("SQL", 0.7, 0.65, True),
        ("Stakeholder Management", 0.7, 0.7, True),
        ("Data Visualization", 0.6, 0.6, False),
        ("Communication", 0.8, 0.8, True),
    ],
    "Cybersecurity Analyst": [
        ("Cybersecurity", 0.9, 0.8, True),
        ("Risk Management", 0.6, 0.6, True),
        ("Python", 0.5, 0.5, False),
        ("AWS", 0.5, 0.5, False),
    ],
}


# --------------------------------------------------------------------------- #
# 2) Organizations
# --------------------------------------------------------------------------- #
# (name, type, tier, industry, size)
EMPLOYERS: list[tuple[str, str, str, str, str]] = [
    ("Petronas", "employer", "GLC", "Oil & Gas", "10000+"),
    ("Maybank", "employer", "GLC", "Banking", "10000+"),
    ("Grab", "employer", "TECH", "Technology", "5000-10000"),
    ("Shopee", "employer", "TECH", "E-commerce", "5000-10000"),
    ("AirAsia", "employer", "LLO", "Aviation", "10000+"),
    ("Sunway Group", "employer", "LLO", "Conglomerate", "5000-10000"),
    ("Kapital DX", "employer", "MNC", "Fintech", "50-200"),
    ("Boost Labs", "employer", "TECH", "Software / MDEC Startup", "11-50"),
]

UNIVERSITIES: list[tuple[str, str, str]] = [
    ("Universiti Malaya", "PUBLIC", "Education"),
    ("Asia Pacific University (APU)", "PRIVATE", "Education"),
    ("Taylor's University", "PRIVATE", "Education"),
    ("Sunway University", "PRIVATE", "Education"),
    ("Multimedia University (MMU)", "PRIVATE", "Education"),
]


# --------------------------------------------------------------------------- #
# 3) Users
# --------------------------------------------------------------------------- #
CANDIDATE_NAMES = [
    "Nurul Izzati binti Hashim",
    "Arjun Nair",
    "Lim Wei Jie",
    "Tan Mei Ling",
    "Muhammad Faiz bin Abdullah",
    "Priya Selvam",
    "Chong Kar Wai",
    "Siti Aminah",
    "Rajesh Kumar",
    "Wong Li Hua",
    "Aaron Tan",
    "Farah Zainal",
    "Goh Yong Sheng",
    "Devi Anand",
    "Hafiz Rahman",
    "Cheryl Ng",
    "Kavin Raj",
    "Nadia Ismail",
    "Brandon Lee",
    "Sharifah Aliyah",
    "Vincent Loh",
    "Aishwarya Pillai",
    "Zulkifli bin Omar",
    "Jessica Teh",
    "Daniel Ong",
    "Mariam Yusof",
    "Kelvin Soh",
    "Anand Krishnan",
    "Lavanya Raman",
    "Ahmad Syafiq",
    "Tania Goh",
    "Hui Ying Lim",
]

LOCATIONS = [
    "Kuala Lumpur",
    "Petaling Jaya",
    "Cyberjaya",
    "Penang",
    "Johor Bahru",
    "Shah Alam",
    "Subang Jaya",
    "Putrajaya",
    "Ipoh",
    "Kuching",
]


# Map candidate index -> (current_occupation_title, target_occupation_title, years_exp)
def _career_for(i: int) -> tuple[str, str, float]:
    profiles = [
        ("Data Analyst", "Data Scientist", 3.0),
        ("Software Engineer", "Senior Software Engineer", 4.0),
        ("Frontend Developer", "Software Engineer", 2.0),
        ("Marketing Executive", "Marketing Manager", 5.0),
        ("Accountant", "Financial Analyst", 6.0),
        ("Backend Developer", "Data Engineer", 3.5),
        ("UX Designer", "Product Designer", 2.5),
        ("Business Analyst", "Product Manager", 4.5),
        ("Senior Data Analyst", "Data Scientist", 6.0),
        ("Registered Nurse", "Registered Nurse", 8.0),
        ("Auditor", "Senior Accountant", 5.0),
        ("Digital Marketing Specialist", "Marketing Manager", 3.0),
        ("Project Manager", "Product Manager", 7.0),
        ("Cybersecurity Analyst", "DevOps Engineer", 2.0),
        ("Data Engineer", "Machine Learning Engineer", 4.0),
    ]
    return profiles[i % len(profiles)]


# --------------------------------------------------------------------------- #
# Embedding helper
# --------------------------------------------------------------------------- #
async def _embed_all(llm, texts: list[str]) -> list[list[float]]:
    """Embed ``texts`` in reasonable batches via the configured LLM client."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start : start + EMBED_BATCH]
        vectors.extend(await llm.embed(batch))
    return vectors


# --------------------------------------------------------------------------- #
# Main seed
# --------------------------------------------------------------------------- #
async def seed(if_empty: bool = False) -> dict[str, int]:  # noqa: C901, PLR0912, PLR0915
    counts: dict[str, int] = {}
    llm = get_llm()

    async with SessionFactory() as session:
        if if_empty:
            existing = await session.scalar(select(func.count()).select_from(User))
            if existing:
                log.info("seed.skip", reason="users_present", users=existing)
                return {"skipped": existing}

        # ---- 1) Taxonomy: skills ----
        skills: dict[str, Skill] = {}
        for name, category, trend in SKILLS:
            s = Skill(
                name=name,
                slug=_slug(name),
                category=category,
                demand_trend=trend,
                description=f"{name} — {category} competency.",
            )
            session.add(s)
            skills[name] = s
        counts["skills"] = len(skills)

        # ---- 1) Taxonomy: occupations ----
        occupations: dict[str, Occupation] = {}
        for title, isco, masco, family, edu, salary in OCCUPATIONS:
            o = Occupation(
                title=title,
                slug=_slug(title),
                isco_code=isco,
                masco_code=masco,
                family=family,
                typical_education=edu,
                median_salary_myr=salary,
                description=f"{title} in the {family} family.",
            )
            session.add(o)
            occupations[title] = o
        counts["occupations"] = len(occupations)
        await session.flush()  # assign skill/occupation ids

        # ---- 1) OccupationSkill links ----
        occ_skill_n = 0
        for occ_title, links in OCC_SKILLS.items():
            occ = occupations[occ_title]
            for skill_name, importance, level, essential in links:
                session.add(
                    OccupationSkill(
                        occupation_id=occ.id,
                        skill_id=skills[skill_name].id,
                        importance=importance,
                        level=level,
                        essential=essential,
                    )
                )
                occ_skill_n += 1
        counts["occupation_skills"] = occ_skill_n

        # ---- 1) OccupationTransition graph ----
        for frm, to, weight, months, delta in TRANSITIONS:
            session.add(
                OccupationTransition(
                    from_occupation_id=occupations[frm].id,
                    to_occupation_id=occupations[to].id,
                    weight=weight,
                    median_months=months,
                    median_salary_delta_pct=delta,
                )
            )
        counts["occupation_transitions"] = len(TRANSITIONS)

        # ---- 2) Organizations ----
        employers: dict[str, Organization] = {}
        for name, otype, tier, industry, size in EMPLOYERS:
            org = Organization(
                name=name,
                type=otype,
                tier=tier,
                industry=industry,
                size=size,
                website=f"https://{_slug(name)}.example.com",
                description=f"{name} — {industry} ({tier}).",
            )
            session.add(org)
            employers[name] = org
        universities: dict[str, Organization] = {}
        for name, tier, industry in UNIVERSITIES:
            org = Organization(
                name=name,
                type="university",
                tier=tier,
                industry=industry,
                website=f"https://{_slug(name)}.example.edu.my",
                description=f"{name} — {tier} university in Malaysia.",
            )
            session.add(org)
            universities[name] = org
        counts["organizations"] = len(employers) + len(universities)
        await session.flush()

        grab = employers["Grab"]
        apu = universities["Asia Pacific University (APU)"]

        # ---- 3) Demo + extra users ----
        pw = hash_password(DEMO_PASSWORD)

        def _user(email: str, name: str, roles: list[str], verified: bool = True) -> User:
            u = User(
                email=email,
                hashed_password=pw,
                full_name=name,
                roles=roles,
                is_active=True,
                is_verified=verified,
                last_login_at=datetime.now(UTC) - timedelta(days=random.randint(0, 14)),
            )
            session.add(u)
            return u

        # Four required demo accounts.
        aisyah = _user("aisyah@demo.atlas", "Aisyah binti Rahman", ["candidate"])
        daniel = _user("daniel@demo.atlas", "Daniel Lim", ["employer_admin"])
        dr_tan = _user("dr.tan@demo.atlas", "Dr. Tan Wei Ming", ["university_admin"])
        admin = _user("admin@demo.atlas", "Platform Admin", ["platform_admin"])

        # A few extra staff/recruiters.
        recruiter_grab = _user("recruiter.grab@demo.atlas", "Mei Chen", ["employer_recruiter"])
        recruiter_shopee = _user(
            "recruiter.shopee@demo.atlas", "Iskandar Halim", ["employer_recruiter"]
        )
        staff_apu = _user("staff.apu@demo.atlas", "Lim Career Services", ["university_staff"])
        admin_maybank = _user("admin.maybank@demo.atlas", "Rohaya Daud", ["employer_admin"])

        # Aisyah is candidate #0; build a full candidate roster including her.
        candidate_users: list[User] = [aisyah]
        for i, full_name in enumerate(CANDIDATE_NAMES):
            email = f"{_slug(full_name).split('-')[0]}{i}@demo.atlas"
            candidate_users.append(_user(email, full_name, ["candidate"]))
        await session.flush()

        # ---- Memberships ----
        memberships = [
            (daniel, grab, "employer_admin", "Head of Talent"),
            (recruiter_grab, grab, "employer_recruiter", "Senior Recruiter"),
            (recruiter_shopee, employers["Shopee"], "employer_recruiter", "Talent Partner"),
            (admin_maybank, employers["Maybank"], "employer_admin", "HR Director"),
            (dr_tan, apu, "university_admin", "Dean of Employability"),
            (staff_apu, apu, "university_staff", "Career Services Officer"),
        ]
        for user, org, role, title in memberships:
            session.add(Membership(user_id=user.id, org_id=org.id, role=role, title=title))
        counts["memberships"] = len(memberships)

        all_user_count = await session.scalar(select(func.count()).select_from(User))
        counts["users"] = int(all_user_count or 0)

        # ---- 4) CandidateProfiles + CareerEvents + CandidateSkills ----
        profiles: list[CandidateProfile] = []
        profile_texts: list[str] = []
        for idx, user in enumerate(candidate_users):
            cur_title, target_title, yoe = _career_for(idx)
            loc = LOCATIONS[idx % len(LOCATIONS)]
            headline = f"{cur_title} | aspiring {target_title}"
            summary = (
                f"{user.full_name.split()[0]} is a {cur_title.lower()} based in {loc} "
                f"with about {yoe:.0f} years of experience, working towards a "
                f"{target_title.lower()} role."
            )
            aspirations = f"Grow into a {target_title} role within the next 2-3 years."
            prof = CandidateProfile(
                user_id=user.id,
                headline=headline,
                summary=summary,
                location=loc,
                aspirations=aspirations,
                current_occupation_id=occupations[cur_title].id,
                target_occupation_id=occupations[target_title].id,
                years_experience=yoe,
                open_to_work=(idx % 3 != 0),
                completeness=random.randint(60, 100),
                links={"linkedin": f"https://linkedin.example/{_slug(user.full_name)}"},
            )
            session.add(prof)
            profiles.append(prof)
            profile_texts.append(f"{headline}. {summary} Skills toward {target_title}.")
        await session.flush()  # assign profile ids

        # Compute + store profile embeddings (batched).
        prof_vectors = await _embed_all(llm, profile_texts)
        for prof, vec in zip(profiles, prof_vectors, strict=False):
            prof.embedding = vec

        # Career events + candidate skills.
        event_n = 0
        cand_skill_n = 0
        for idx, (_user, prof) in enumerate(zip(candidate_users, profiles, strict=False)):
            cur_title, target_title, yoe = _career_for(idx)
            today = date(2026, 6, 1)
            # Education event.
            grad_year = 2026 - int(yoe) - random.randint(0, 2)
            uni_name = list(universities.keys())[idx % len(universities)]
            session.add(
                CareerEvent(
                    candidate_id=prof.id,
                    type="education",
                    title="Bachelor's Degree",
                    organization=uni_name,
                    start_date=date(grad_year - 4, 9, 1),
                    end_date=date(grad_year, 7, 1),
                    narrative="Foundational study relevant to current career track.",
                    highlights=["Dean's List", "Final-year project"],
                )
            )
            event_n += 1
            # Optional career break for some candidates.
            cursor = date(grad_year, 8, 1)
            if idx % 7 == 3:
                brk_end = cursor + timedelta(days=365)
                session.add(
                    CareerEvent(
                        candidate_id=prof.id,
                        type="break",
                        title="Career Break",
                        start_date=cursor,
                        end_date=brk_end,
                        is_current=False,
                        break_reason=random.choice(["caregiving", "study", "health"]),
                        narrative="A deliberate pause; returned with renewed focus.",
                    )
                )
                event_n += 1
                cursor = brk_end
            # First role + current role.
            first_role = cur_title if random.random() < 0.5 else "Software Engineer"
            session.add(
                CareerEvent(
                    candidate_id=prof.id,
                    type="role",
                    title=first_role,
                    organization=random.choice(list(employers.keys())),
                    occupation_id=occupations.get(first_role, occupations[cur_title]).id,
                    start_date=cursor,
                    end_date=today - timedelta(days=int(yoe * 120)),
                    narrative="Built core competencies and delivered on key projects.",
                    highlights=["Shipped a flagship feature", "Mentored 2 juniors"],
                    skills_used=[s for s, *_ in OCC_SKILLS.get(first_role, [])][:3],
                )
            )
            event_n += 1
            session.add(
                CareerEvent(
                    candidate_id=prof.id,
                    type="role",
                    title=cur_title,
                    organization=random.choice(list(employers.keys())),
                    occupation_id=occupations[cur_title].id,
                    start_date=today - timedelta(days=int(yoe * 120)),
                    is_current=True,
                    narrative="Current role; driving measurable impact and upskilling.",
                    highlights=["Led a cross-functional initiative"],
                    skills_used=[s for s, *_ in OCC_SKILLS.get(cur_title, [])][:4],
                )
            )
            event_n += 1
            # A project event for variety.
            if idx % 2 == 0:
                session.add(
                    CareerEvent(
                        candidate_id=prof.id,
                        type="project",
                        title="Side Project: Open-source contribution",
                        start_date=today - timedelta(days=200),
                        end_date=today - timedelta(days=60),
                        narrative="Self-directed project to build target-role skills.",
                        skills_used=[s for s, *_ in OCC_SKILLS.get(target_title, [])][:2],
                    )
                )
                event_n += 1

            # Candidate skills: blend of current + target-role skills.
            seen: set[str] = set()
            for skill_name, _importance, level, _essential in OCC_SKILLS.get(
                cur_title, []
            ) + OCC_SKILLS.get(target_title, []):
                if skill_name in seen:
                    continue
                seen.add(skill_name)
                evidence = random.choice(["asserted", "asserted", "verified", "inferred"])
                session.add(
                    CandidateSkill(
                        candidate_id=prof.id,
                        skill_id=skills[skill_name].id,
                        proficiency=round(min(0.95, level * random.uniform(0.7, 1.1)), 2),
                        evidence_type=evidence,
                        confidence=round(random.uniform(0.5, 0.95), 2),
                        years=round(min(yoe, random.uniform(0.5, yoe + 0.5)), 1),
                    )
                )
                cand_skill_n += 1
        counts["candidate_profiles"] = len(profiles)
        counts["career_events"] = event_n
        counts["candidate_skills"] = cand_skill_n
        await session.flush()

        # Profile embeddings also into the RAG corpus (career_history).
        for prof, vec, text in zip(profiles, prof_vectors, profile_texts, strict=False):
            session.add(
                Embedding(
                    owner_type="career_history",
                    owner_id=prof.id,
                    chunk=text,
                    vector=vec,
                    meta={"kind": "profile_summary"},
                )
            )
        counts["embeddings_profiles"] = len(profiles)

        # ---- 5) Jobs ----
        # (title, employer, seniority, work_mode, comp_min, comp_max, internship)
        job_specs: list[tuple[str, str, str, str, int, int, bool]] = []
        emp_names = list(employers.keys())
        job_titles_pool = [
            ("Software Engineer", "entry", 5500, 8000),
            ("Senior Software Engineer", "senior", 10000, 15000),
            ("Frontend Developer", "mid", 6000, 9000),
            ("Backend Developer", "mid", 6500, 9500),
            ("DevOps Engineer", "mid", 8000, 12000),
            ("Data Analyst", "entry", 4500, 7000),
            ("Senior Data Analyst", "senior", 7500, 11000),
            ("Data Scientist", "mid", 8500, 13000),
            ("Machine Learning Engineer", "senior", 11000, 17000),
            ("Data Engineer", "mid", 8000, 12000),
            ("Product Manager", "senior", 10000, 16000),
            ("Product Designer", "mid", 6500, 10000),
            ("UX Designer", "mid", 6000, 9000),
            ("Marketing Executive", "entry", 3800, 5500),
            ("Marketing Manager", "senior", 8000, 13000),
            ("Digital Marketing Specialist", "mid", 5000, 7500),
            ("Accountant", "entry", 4200, 6000),
            ("Senior Accountant", "senior", 6500, 9500),
            ("Financial Analyst", "mid", 5500, 8500),
            ("Cybersecurity Analyst", "mid", 7000, 11000),
        ]
        # ~40 jobs: each title roughly twice across different employers.
        for round_no in range(2):
            for ti, (title, sen, cmin, cmax) in enumerate(job_titles_pool):
                emp = emp_names[(ti + round_no) % len(emp_names)]
                job_specs.append(
                    (title, emp, sen, "hybrid" if ti % 2 else "onsite", cmin, cmax, False)
                )

        jobs: list[Job] = []
        job_texts: list[str] = []
        work_modes = ["onsite", "hybrid", "remote"]
        for ji, (title, emp_name, sen, _wm, cmin, cmax, intern) in enumerate(job_specs):
            occ = occupations[title]
            req_skills = [s for s, *_ in OCC_SKILLS.get(title, [])]
            poster = daniel if emp_name == "Grab" else None
            wm = work_modes[ji % 3]
            growth = [to for frm, to, *_ in TRANSITIONS if frm == title][:2]
            desc = (
                f"{emp_name} is hiring a {title} ({sen}). You'll work on impactful "
                f"products in a {wm} setting in Malaysia. Median market salary anchor "
                f"~RM{occ.median_salary_myr}/month."
            )
            job = Job(
                org_id=employers[emp_name].id,
                posted_by=poster.id if poster else None,
                title=title,
                occupation_id=occ.id,
                description=desc,
                responsibilities=[
                    f"Own {title.lower()} deliverables end to end.",
                    "Collaborate cross-functionally.",
                    "Drive measurable outcomes.",
                ],
                requirements=[
                    f"Experience as a {title}.",
                    "Strong communication skills.",
                    f"Familiarity with {', '.join(req_skills[:3])}.",
                ],
                skills_required=req_skills,
                location=LOCATIONS[ji % len(LOCATIONS)],
                work_mode=wm,
                seniority=sen,
                comp_min=cmin,
                comp_max=cmax,
                status="open",
                is_internship=intern,
                growth_into=growth,
                views=random.randint(5, 400),
                closes_at=datetime.now(UTC) + timedelta(days=random.randint(7, 45)),
            )
            session.add(job)
            jobs.append(job)
            job_texts.append(f"{title} at {emp_name}. {desc} Skills: {', '.join(req_skills)}.")
        await session.flush()

        job_vectors = await _embed_all(llm, job_texts)
        for job, vec, text in zip(jobs, job_vectors, job_texts, strict=False):
            job.embedding = vec
            session.add(
                Embedding(
                    owner_type="job_posting",
                    owner_id=job.id,
                    chunk=text,
                    vector=vec,
                    meta={"title": job.title},
                )
            )
        counts["jobs"] = len(jobs)
        counts["embeddings_jobs"] = len(jobs)

        # ---- 6) Applications + ApplicationEvents (~60, all statuses) ----
        app_n = 0
        appevent_n = 0
        status_cycle = list(APPLICATION_STATUSES)
        # Status -> ordered path of prior stages for a believable timeline.
        status_path = {
            "applied": ["applied"],
            "screening": ["applied", "screening"],
            "shortlisted": ["applied", "screening", "shortlisted"],
            "interview": ["applied", "screening", "shortlisted", "interview"],
            "offer": ["applied", "screening", "shortlisted", "interview", "offer"],
            "hired": ["applied", "screening", "shortlisted", "interview", "offer", "hired"],
            "rejected": ["applied", "screening", "rejected"],
            "withdrawn": ["applied", "withdrawn"],
        }
        used_pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()
        target = 60
        attempts = 0
        while app_n < target and attempts < target * 5:
            attempts += 1
            prof = random.choice(profiles)
            job = random.choice(jobs)
            pair = (prof.id, job.id)
            if pair in used_pairs:
                continue
            used_pairs.add(pair)
            status = status_cycle[app_n % len(status_cycle)]
            datetime.now(UTC) - timedelta(days=random.randint(2, 90))
            feedback = None
            if status in ("rejected", "offer", "hired"):
                feedback = (
                    "Strong profile; pipeline very competitive this cycle."
                    if status == "rejected"
                    else "Great fit — looking forward to onboarding."
                )
            application = Application(
                candidate_id=prof.id,
                job_id=job.id,
                status=status,
                cover_note=f"I'm excited about the {job.title} role and a strong match.",
                feedback=feedback,
                source=random.choice(["atlas", "atlas", "referral"]),
            )
            session.add(application)
            await session.flush()
            app_n += 1
            # Build the event timeline.
            path = status_path[status]
            prev = None
            for _step, st in enumerate(path):
                session.add(
                    ApplicationEvent(
                        application_id=application.id,
                        from_status=prev,
                        to_status=st,
                        note=f"Moved to {st}.",
                        actor_id=(daniel.id if job.org_id == grab.id and st != "applied" else None),
                    )
                )
                prev = st
                appevent_n += 1
        counts["applications"] = app_n
        counts["application_events"] = appevent_n

        # ---- 7) Cohorts + CohortStudents + Outcomes + Internships ----
        cohort_n = 0
        cohort_student_n = 0
        outcome_n = 0
        cohorts: list[Cohort] = []
        programs = [
            ("BSc Computer Science", "Computing", "bachelor"),
            ("BSc Data Science", "Computing", "bachelor"),
            ("BBA Marketing", "Business", "bachelor"),
            ("BAcc Accounting", "Business", "bachelor"),
        ]
        for uni in universities.values():
            for year in (2022, 2023, 2024):
                program, faculty, level = random.choice(programs)
                c = Cohort(
                    university_org_id=uni.id,
                    program=program,
                    faculty=faculty,
                    graduation_year=year,
                    level=level,
                )
                session.add(c)
                cohorts.append(c)
                cohort_n += 1
        await session.flush()

        # Enroll candidates into cohorts of their alma mater and record outcomes.
        for idx, prof in enumerate(profiles):
            cohort = cohorts[idx % len(cohorts)]
            session.add(
                CohortStudent(
                    cohort_id=cohort.id,
                    candidate_id=prof.id,
                    student_ref=f"S{cohort.graduation_year}{idx:03d}",
                )
            )
            cohort_student_n += 1
            cur_title, _t, _y = _career_for(idx)
            outcome_status = random.choice(
                ["employed", "employed", "employed", "further_study", "seeking", "entrepreneur"]
            )
            session.add(
                Outcome(
                    candidate_id=prof.id,
                    cohort_id=cohort.id,
                    captured_at=date(cohort.graduation_year + 1, 1, 15),
                    status=outcome_status,
                    role_title=cur_title if outcome_status == "employed" else None,
                    employer_name=(
                        random.choice(list(employers.keys()))
                        if outcome_status == "employed"
                        else None
                    ),
                    salary_myr=(
                        occupations[cur_title].median_salary_myr
                        if outcome_status == "employed"
                        else None
                    ),
                    months_to_employment=random.randint(0, 9),
                    field_relevant=random.choice([True, True, False, None]),
                )
            )
            outcome_n += 1
        counts["cohorts"] = cohort_n
        counts["cohort_students"] = cohort_student_n
        counts["outcomes"] = outcome_n

        internships = [
            (
                "Software Engineering Intern",
                grab,
                ["Python", "React"],
                ["Software Engineer"],
                6,
                1800,
            ),
            (
                "Data Analytics Intern",
                employers["Shopee"],
                ["SQL", "Power BI"],
                ["Data Analyst"],
                4,
                1500,
            ),
            (
                "Marketing Intern",
                employers["AirAsia"],
                ["Digital Marketing"],
                ["Marketing Executive"],
                3,
                1200,
            ),
            (
                "Finance Intern",
                employers["Maybank"],
                ["Accounting", "Excel"],
                ["Accountant"],
                6,
                1400,
            ),
        ]
        for title, org, focus, grows, months, stipend in internships:
            session.add(
                Internship(
                    org_id=org.id,
                    title=title,
                    description=f"{title} at {org.name} — hands-on, mentored placement.",
                    skills_focus=focus,
                    grows_into=grows,
                    location=random.choice(LOCATIONS),
                    duration_months=months,
                    stipend_myr=stipend,
                    status="open",
                )
            )
        counts["internships"] = len(internships)

        # ---- 8) Signals (Grab candidates), Notifications, Consent, Credentials ----
        # Pick a handful of candidates "within Grab" context for signals.
        signal_types = [
            "activity_drop",
            "onboarding_risk",
            "plateau",
            "underpaid",
            "peer_departure",
        ]
        signal_n = 0
        for prof in profiles[:8]:
            stype = signal_types[signal_n % len(signal_types)]
            session.add(
                Signal(
                    subject_candidate_id=prof.id,
                    org_id=grab.id,
                    type=stype,
                    strength=round(random.uniform(0.4, 0.9), 2),
                    summary={
                        "activity_drop": "Engagement down vs. their 90-day baseline.",
                        "onboarding_risk": "Early-tenure ramp slower than cohort median.",
                        "plateau": "No role change or new verified skill in 18 months.",
                        "underpaid": "Comp trails market median for the role and tenure.",
                        "peer_departure": "Two close collaborators recently departed.",
                    }[stype],
                    evidence={"window_days": 90, "baseline": "cohort_median"},
                    status=random.choice(["open", "open", "acknowledged"]),
                )
            )
            signal_n += 1
        counts["signals"] = signal_n

        # Notifications for the demo users.
        notif_specs = [
            (
                aisyah,
                "match",
                "New high-fit role at Grab",
                "A Data Scientist role matches your trajectory.",
                "/jobs",
            ),
            (
                aisyah,
                "coach_nudge",
                "Sharpen your skill graph",
                "Verify 2 skills to lift your match score.",
                "/profile",
            ),
            (
                aisyah,
                "application",
                "Your application advanced",
                "You moved to the interview stage.",
                "/applications",
            ),
            (
                daniel,
                "signal",
                "Retention signal in your team",
                "A team member shows a plateau signal.",
                "/signals",
            ),
            (
                daniel,
                "application",
                "New applicant",
                "A strong candidate applied to your Data Scientist role.",
                "/applications",
            ),
            (
                dr_tan,
                "system",
                "Outcomes report ready",
                "2024 cohort employability summary is available.",
                "/outcomes",
            ),
            (admin, "system", "Weekly platform digest", "Usage and cost ledger updated.", "/admin"),
        ]
        for user, ntype, title, body, link in notif_specs:
            session.add(
                Notification(
                    user_id=user.id,
                    type=ntype,
                    title=title,
                    body=body,
                    link=link,
                    is_read=random.choice([False, False, True]),
                    payload={"seeded": True},
                )
            )
        counts["notifications"] = len(notif_specs)

        # Consent grants: several candidates grant Grab profile/skills/trajectory.
        consent_n = 0
        for prof in profiles[:12]:
            session.add(
                ConsentGrant(
                    candidate_id=prof.id,
                    grantee_org_id=grab.id,
                    scopes=["profile", "skills", "trajectory"],
                    purpose="Talent discovery for relevant open roles at Grab.",
                    expires_at=datetime.now(UTC) + timedelta(days=180),
                )
            )
            consent_n += 1
        # Aisyah also grants Shopee for a richer demo.
        session.add(
            ConsentGrant(
                candidate_id=profiles[0].id,
                grantee_org_id=employers["Shopee"].id,
                scopes=["profile", "skills"],
                purpose="Consideration for matching roles.",
                expires_at=datetime.now(UTC) + timedelta(days=90),
            )
        )
        consent_n += 1
        counts["consent_grants"] = consent_n

        # A few verifiable credentials issued by APU.
        cred_n = 0
        for prof in profiles[:6]:
            session.add(
                Credential(
                    issuer_org_id=apu.id,
                    holder_candidate_id=prof.id,
                    type=random.choice(["degree", "micro_credential", "certificate"]),
                    title=random.choice(
                        ["Cloud Fundamentals", "Data Analytics Micro-credential", "BSc (Hons)"]
                    ),
                    description="Issued and mock-signed for the demo (OBv3-style).",
                    skill_slugs=[_slug("SQL"), _slug("Python")],
                    proof={"type": "MockSignature2025", "verified": True},
                    issued_at=datetime.now(UTC) - timedelta(days=random.randint(30, 700)),
                    status="active",
                )
            )
            cred_n += 1
        counts["credentials"] = cred_n

        # Seed a little usage + audit history so admin screens aren't empty.
        for feature in ("coach", "matching", "trajectory", "skill_halflife"):
            session.add(
                LlmUsage(
                    org_id=grab.id,
                    user_id=daniel.id,
                    feature=feature,
                    model="mock-llm",
                    prompt_tokens=random.randint(200, 1200),
                    completion_tokens=random.randint(80, 400),
                    cost_usd=round(random.uniform(0.001, 0.02), 6),
                )
            )
        session.add(
            AuditLog(
                actor_id=daniel.id,
                org_id=grab.id,
                action="talent_search",
                resource_type="candidate_profile",
                detail={"query": "data scientist", "results": 5},
            )
        )
        counts["llm_usage"] = 4
        counts["audit_logs"] = 1

        await session.commit()

    return counts


async def main() -> None:
    if_empty = "--if-empty" in sys.argv
    # Register all model metadata (schema itself is created by init_db / Alembic).
    import_all_models()
    log.info("seed.start", if_empty=if_empty)
    counts = await seed(if_empty=if_empty)
    await engine.dispose()
    if counts.get("skipped"):
        print(f"Seed skipped: {counts['skipped']} users already present.")
        return
    print("\n=== Atlas demo seed complete ===")
    width = max((len(k) for k in counts), default=10)
    for key in sorted(counts):
        print(f"  {key.ljust(width)} : {counts[key]}")
    print(
        "\nDemo logins (password 'demo1234'):\n"
        "  aisyah@demo.atlas   (candidate)\n"
        "  daniel@demo.atlas   (employer_admin @ Grab)\n"
        "  dr.tan@demo.atlas   (university_admin @ APU)\n"
        "  admin@demo.atlas    (platform_admin)\n"
    )


if __name__ == "__main__":
    asyncio.run(main())
