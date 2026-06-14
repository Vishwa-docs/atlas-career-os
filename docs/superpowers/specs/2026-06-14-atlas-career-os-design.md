# Atlas — Asia's Career OS · Design Spec

**Status:** Approved-for-planning draft
**Date:** 2026-06-14
**Author:** Atlas Team (Talentbank Tech Hackathon, First Cohort)
**Tagline:** *A map, not a fortune-teller. One career graph. Three control rooms.*

---

## 0. Document purpose

This is the single source of truth for what Atlas is, why it wins, and how it is built. It drives the implementation plan. It is written to read cleanly to someone who did not write it (per the hackathon's Code Quality criterion) and to be directly integrable into Talentbank's stack (per Completeness).

---

## 1. Problem & thesis

### 1.1 The problem (from the brief, sharpened by research)
Careers are built "spontaneously, unpredictably, alone." The systems between people and opportunity were never built to see the whole picture: **job boards see jobs, ATS sees filters, universities see graduation. Nobody sees a career as one continuous thing.**

Competitive research confirms the gap is *structural*, not incremental:
- **Everything is episodic.** LinkedIn/Indeed optimize *this requisition*. Teal/Huntr trackers go dormant once you're hired. Handshake/Symplicity/12twenty abandon the student at first-destination. The 40-year longitudinal layer is unclaimed.
- **The skills graph is enterprise-locked.** Gloat/Eightfold/Fuel50 only work inside 1,000+-employee firms with rich HRIS data. Graduates and SME workers are unserved.
- **The university→work cliff.** No platform carries a verified academic-skills record forward into a lifelong, candidate-owned profile.
- **Human-mentorship economics are broken** (Pathrise wound down in 2025). AI can deliver that guidance at marginal cost.
- **APAC has no continuous navigator.** Jobstreet/SEEK, Glints, Kalibrr, Foundit are all transactional.

### 1.2 The thesis (our wedge)
**The Career Graph** — one portable, candidate-*owned*, continuously-updated graph of a person's skills, achievements, roles, and trajectory, spanning a 40-year arc, legible *with consent* to employers and universities. Every Atlas module is a **lens on this one shared graph**, not a bolted-on feature. Talentbank's 100+ universities + 10,000+ employers in a single graph is a moat incumbents cannot structurally copy — they each own only one or two sides.

### 1.3 Three non-negotiable product commitments (answering Ben directly)
1. **Glass Box, never black box.** Every AI output ships with a plain-language **rationale + evidence citations + a confidence band + "what would change this."** No naked scores. No false precision.
2. **Ranges, not answers.** We surface the realistic *spread* of outcomes for "people of similar shape" with explicit trade-offs. The user always chooses (navigation, not prediction).
3. **Data dignity.** The candidate owns the graph. Granular, time-boxed, revocable consent governs who sees what. PDPA (Malaysia) / GDPR-native, with full export and erasure.

---

## 2. Personas & journeys

### 2.1 End-user personas
- **Aisyah, 21, final-year CS, UM (Candidate / Student).** Wants a first job that goes somewhere, not just any job. Doesn't know her market value or realistic next moves.
- **Wei Jie, 34, mid-career analyst (Candidate / Professional).** Feels plateaued, suspects he's underpaid, unsure whether to pivot.
- **Priya, 41, returning after a 2-year caregiving break (Candidate / Re-entry).** Needs a plan that respects the break and a way to prove current capability.
- **Daniel, recruiter at a Tier-3 LLO (Employer / Recruiter).** Drowns in keyword-matched noise; wants people on the right *trajectory*, and to keep the good ones.
- **Mei Ling, HR director (Employer / Admin).** Worried about attrition, onboarding churn, and a shrinking working-age population over the next decade.
- **Dr. Tan, career-services lead, APU (University / Staff).** Tracks outcomes for ~1 year then goes blind; wants to prove employability and intervene early.
- **Prof. Rao, faculty (University / Faculty).** Wants to teach what the market will need in 3 years, not what it needed 3 years ago.
- **Platform Admin (Talentbank ops).** Manages tenants, taxonomy, moderation, AI cost/usage, audit.

### 2.2 The four control rooms
| Audience | Control room | Core promise |
|---|---|---|
| Candidate | **Navigator** | "See your realistic next moves, know your worth, and have a coach watching your back for decades." |
| Employer | **Talent Radar** | "Find people heading where the role leads, spot flight risk early, and plan a workforce that survives demographics." |
| University | **Outcomes Studio** | "Watch outcomes for decades, teach to where the market is going, and prove your graduates are ready." |
| Admin | **Mission Control** | "Run the platform: tenants, taxonomy, trust, AI cost, audit." |

---

## 3. Feature catalog (120+ items, tiered)

**Tier A** = production-deep, end-to-end, demoable. **Tier B** = functional, lighter, honestly labeled. **Tier C** = designed + scaffolded (API/stub/UI shell) with clear extension points. All over the one Career Graph + AI spine.

### 3.1 Foundation & cross-cutting (Tier A unless noted)
1. Email/password sign-up + login (OAuth2 password flow)
2. Short-lived JWT access + rotating refresh tokens with reuse detection
3. Argon2id password hashing
4. Multi-role RBAC: `candidate`, `employer_recruiter`, `employer_admin`, `university_staff`, `university_admin`, `platform_admin`
5. Organization/tenant model (employers, universities) with `org_id` scoping
6. Postgres Row-Level Security backstop on sensitive tables
7. Email verification + password reset flows
8. Per-object authorization (BOLA defense) on every fetch
9. Rate limiting (auth + AI endpoints tighter)
10. Audit log (append-only) for all access to career data
11. **Consent & Data Dignity Center**: granular, time-boxed, revocable grants (per-employer, per-university, per-field)
12. Data export (portability) + account erasure (right to be forgotten)
13. Notification center (in-app) + WebSocket live updates
14. Email digests (ARQ scheduled)
15. Global search (people/jobs/orgs scoped by role)
16. Internationalization scaffolding: EN / Malay / 中文
17. Accessibility: WCAG-minded components, keyboard nav, ARIA, contrast
18. Dark / light theme
19. Responsive (mobile → desktop)
20. **Glass Box** explainability component reused across all AI surfaces (rationale + citations + confidence + "what would change this")
21. **AI provenance manifest** surfaced in UI + docs (model, prompt purpose, guardrails)
22. Feature flags
23. Onboarding wizard per role
24. Activity timeline (the user's own graph history)

### 3.2 The Career Graph & taxonomy (Tier A — the spine)
25. Skills taxonomy seeded from O*NET + ESCO subset, normalized via Lightcast-style IDs
26. Occupation taxonomy with ISCO-08 pivot → MASCO (Malaysia) crosswalk
27. Skill ↔ occupation bipartite edges (essential/optional, importance/level)
28. Job-to-job transition graph with empirical transition weights
29. Candidate career-history timeline (roles, tenure, achievements, education)
30. Skill proficiency + evidence model (self-asserted, verified, inferred)
31. Embeddings store (pgvector, HNSW, versioned embedding model)
32. Skill decay / **Skill Half-Life** tracking from postings trends
33. "People like you" cohort engine (anonymized aggregate trajectories by shape)

### 3.3 Candidate · Navigator
**Core jobsite (Tier A)**
34. Profile builder (structured, guided, completeness meter)
35. **LLM résumé parsing** → structured graph (schema-first, grounded, confidence-flagged)
36. Multi-version résumé / CV builder + export (PDF)
37. Job listings browse + filters
38. **Hybrid semantic + keyword job search** (pgvector + BM25 + RRF)
39. Natural-language job search ("remote data role that grows into ML")
40. Saved searches + job alerts
41. One-click apply + application tracker (Kanban)
42. Application status timeline + feedback loop
43. **Trajectory-aware match score** with Glass Box explanation per job
44. Candidate dashboard (applications, matches, nudges, market snapshot)

**Signature AI (Tier A)**
45. **Trajectory Atlas** *(Career Path Navigator)* — interactive constellation of realistic next moves; each route shows salary range, time-to-reach band, feasibility, required-skill gap, and trade-offs
46. **Pivot Feasibility + ramp** — "to move X→Y, here's the gap and a realistic learning path," with ranges
47. **Career Copilot** *(AI Career Coach)* — streaming chat, tool-use over your graph + market data; cites sources; shows uncertainty
48. Proactive coach nudges (plateau detected, underpaid signal, a role you'd fit opened) — quiet by default, opt-in
49. **Fair Pay Engine** — DOSM-anchored market range for role/region/experience/skills; P25/P50/P75 with confidence
50. Negotiation coach + timing ("raise it before your review; here's the script & evidence")
51. **Career Weather** — plain-language local market briefing for your role (demand, emerging skills, salary drift)

**Tier B**
52. **Living Portfolio** — running record of projects/decisions/things you led
53. Work-journal quick capture → AI compiles into evidence
54. GitHub / link import → portfolio evidence
55. Self-writing CV (always-true, compiled from the graph)
56. **Life Chapter Designer** — plan around family/health/study/sabbatical breaks
57. Re-entry ramp planner + "career runway" budgeting
58. Skill-gap learning recommendations (mapped to taxonomy)
59. Interview prep helper (role-specific, from the JD + your graph)
60. Cover-letter drafting grounded in your evidence (no fabrication)
61. **Alumni Mentor Match** (similar-trajectory alumni)
62. Peer cohort benchmarking ("people like you" outcomes)

**Tier C**
63. Verifiable credential wallet (holder side) — see §3.6
64. Public shareable profile (consent-gated)
65. Calendar/interview scheduling

### 3.4 Employer · Talent Radar
**Core (Tier A)**
66. Employer org onboarding + team management (recruiter/admin)
67. Job posting CRUD + lifecycle (draft/open/closed)
68. **Bias & Fairness Auditor** — de-bias job-description language before posting
69. Candidate pipeline / funnel CRM (stages, notes, collaboration)
70. **Smart Talent Matching** — trajectory-aware, two-sided fit, fully explainable
71. Semantic candidate search over consented profiles
72. Employer dashboard (open roles, pipeline health, time-to-fill)
73. AI-drafted, personalized outreach (grounded, non-spammy)
74. Shortlist + adverse-impact check (Glass Box)

**Tier B**
75. **Talent Retention Signals** — consented quiet signals (activity drop, peers leaving, profile updates) → manager nudge while there's time
76. Retention conversation prompts (manager talking points)
77. **Talent Re-Engagement** — opt-in "warm bench"; warm restart when a fitting role opens
78. **Onboarding Success Predictor** — first-60-day risk flags + support suggestions
79. **Hidden-Talent surfacing** — strong non-linear / non-traditional paths

**Tier C**
80. **Workforce Resilience Planner** — UN WPP demographic scenarios (hire/retain/AI/migrate) over 10–30 yrs with charts
81. Employer benchmarking (vs Talentbank-style aggregate)
82. Headcount/skills scenario sandbox
83. ATS export / webhook integration points

### 3.5 University · Outcomes Studio
**Core (Tier A)**
84. University org + cohort/program model
85. Student roster + invitations
86. **Adaptive Readiness Profile** — live employability signal growing with the student
87. **Lifelong Outcome Loop** — graduate outcome tracking dashboard (first-destination → decades)
88. Outcomes analytics (employment rate, time-to-employ, salary, fields)

**Tier B**
89. **Future-State Curriculum Engine** — live postings + skills trends → forward-projected curriculum gaps for faculty
90. Program-vs-market skill-coverage heatmap
91. **Live Internship Marketplace** — two-sided student↔internship matching ("dating-app style")
92. Placement-quality tracking ("which placements lead somewhere")
93. Employer relationship CRM (university side)

**Tier C**
94. **Lifelong Learning Wallet** — issuer + verifier of W3C VC / Open Badges 3.0 (see §3.6)
95. Curriculum recommendation export
96. Cohort outcome comparison vs national benchmark
97. Career-fair / event module

### 3.6 Credentials (Tier C, designed end-to-end)
98. Issue Open Badges 3.0 credentials (university as issuer), skills referenced to taxonomy IDs
99. Holder wallet (candidate) stores VCs
100. Verifier checks cryptographic proof (tamper-evident, no issuer callback)
101. Credentials feed skill-gap + matching engines (machine-readable, not static badges)
102. Re-verification / expiry prompts (the "degree that keeps learning")

### 3.7 Admin · Mission Control
103. Tenant management (employers, universities)
104. User moderation + role assignment
105. Taxonomy management (skills/occupations/crosswalks)
106. Content moderation queue (jobs, profiles)
107. **AI usage & cost dashboard** (per-org `llm_usage` ledger)
108. Audit-log explorer
109. Feature-flag console
110. System health / metrics

### 3.8 AI & platform craft (Tier A)
111. `LLMClient` Protocol → `AzureOpenAIClient` (swappable provider)
112. SSE streaming chat to React
113. Structured outputs (`parse()`/json_schema) for all AI verdicts → `{rationale, citations[], confidence}`
114. Tool/function calling (search_jobs, get_salary_band, get_trajectory, get_cohort)
115. RAG over career history + job corpus + market data (hybrid + RRF, structure-aware chunking)
116. Prompt-injection defense (delimited untrusted content; retrieved text can't alter instructions)
117. PII redaction before logging
118. Tenacity retries + timeouts + Retry-After
119. Embedding + completion caching (content hash / Redis)
120. Re-embedding on content change + model upgrade (versioned)
121. Guardrails: refuse fabrication, ground every claim, surface uncertainty
122. Cost ceilings + token budgets per request

> **120+ features confirmed.** Full per-feature acceptance criteria are expanded in the implementation plan.

---

## 4. Data model (core entities)

- **User** (id, email, hashed_password, roles[], locale, created_at) — auth identity
- **Organization** (id, type[employer|university], name, tier, country) — tenant
- **Membership** (user_id, org_id, role) — user↔org
- **CandidateProfile** (user_id, headline, summary, location, aspirations, completeness)
- **CareerEvent** (candidate_id, type[role|education|project|break|credential], title, org, start, end, narrative, evidence[])
- **Skill** (id, name, external_ids{onet,esco,lightcast}, category)
- **Occupation** (id, title, isco_code, masco_code, onet_soc)
- **OccupationSkill** (occupation_id, skill_id, importance, level, essential)
- **OccupationTransition** (from_occupation_id, to_occupation_id, weight, median_months, median_salary_delta)
- **CandidateSkill** (candidate_id, skill_id, proficiency, evidence_type[asserted|verified|inferred], confidence)
- **Job** (id, org_id, title, occupation_id, description, location, comp_min, comp_max, status, embedding)
- **Application** (candidate_id, job_id, status, timeline[], feedback)
- **MatchResult** (candidate_id, job_id, score, rationale, citations[], confidence) — cached, explainable
- **ConsentGrant** (candidate_id, grantee_org_id, scope[], granted_at, expires_at, revoked_at)
- **Signal** (subject_id, type[activity_drop|peer_departure|profile_update|underpaid|plateau], strength, observed_at)
- **Credential** (issuer_org_id, holder_id, type, skills[], proof, issued_at, expires_at)
- **Cohort** (university_org_id, program, year, students[])
- **Outcome** (candidate_id, cohort_id, first_destination, current_role, salary_band, captured_at)
- **LlmUsage** (org_id, endpoint, model, prompt_tokens, completion_tokens, cost, at)
- **AuditLog** (actor_id, action, resource, org_id, at) — append-only
- **Embedding** (owner_type, owner_id, model_version, vector, chunk, metadata)

Two embedding-bearing corpora minimum: candidate career text and job descriptions, plus a market/data corpus for RAG grounding.

---

## 5. System architecture

### 5.1 Components
- **Frontend** — React + Vite + TS SPA; four role-scoped apps (Navigator, Talent Radar, Outcomes Studio, Mission Control) sharing a component library.
- **Backend** — FastAPI, domain-based modules, async SQLAlchemy 2.0, served by uvicorn.
- **Database** — PostgreSQL + pgvector (Neon), Alembic migrations.
- **AI** — Azure OpenAI behind `LLMClient` Protocol.
- **Jobs** — ARQ workers + Redis (signals, digests, re-embedding, notifications, cron).
- **Realtime** — SSE (LLM streaming), WebSockets + Redis pub/sub (notifications, live dashboards).

### 5.2 Backend layout
```
backend/app/
  main.py                 # app factory, lifespan, middleware, router mount
  core/                   # config, security, db, logging, exceptions, deps
  domains/
    auth/  candidates/  employers/  universities/
    jobs/  matching/  signals/  credentials/  consent/
    notifications/  admin/  taxonomy/
    ai/{ llm/{client.py, azure.py, prompts/, schemas.py}, rag/, guardrails.py }
  workers/                # arq settings + tasks
  api/router.py           # aggregates domain routers under /api/v1
alembic/  tests/  pyproject.toml  Dockerfile
```
Each domain: `router · service · repository · schemas · models · deps`. Routers thin; services hold logic; repositories own all DB queries; commit at the service boundary.

### 5.3 Frontend layout
```
frontend/src/
  app/         # router, providers, layout shells per role
  features/    # auth, candidate, employer, university, admin, matching, chat, ...
               #   each: api.ts (query hooks), components/, schemas.ts, types.ts
  components/ui/   # shadcn primitives
  lib/         # apiClient, queryClient, sse, i18n, utils
  hooks/  stores/  types/
```

### 5.4 AI subsystem
- **Abstraction:** `LLMClient` Protocol (`chat`, `stream_chat`, `embed`, `structured`, `tools`) → `AzureOpenAIClient` (official `openai` SDK, `AsyncAzureOpenAI`). Mockable in tests.
- **Structured everything:** AI verdicts use `parse()`/json_schema → Pydantic models carrying `rationale`, `citations[]`, `confidence`. The UI renders these via the shared Glass Box component.
- **RAG:** structure-aware chunking; embed with `text-embedding-3-large` (dimensions trimmed for storage); HNSW + Postgres FTS; fuse via RRF (k=60); optional LLM rerank of top ~50.
- **Guardrails:** delimited untrusted content; retrieved text never alters system instructions; PII redaction in logs; refuse fabrication; ground claims; surface uncertainty.
- **Reliability/cost:** tenacity retries (429/5xx/timeout, honor Retry-After), per-request token caps, `llm_usage` ledger, embedding/completion caching.

### 5.5 Deployment
- **Frontend → Vercel** (Vite SPA, preview deploys).
- **Postgres → Neon** (pgvector enabled, branchable).
- **Backend → Render** (Dockerized FastAPI web service + separate ARQ worker from same image; managed Redis add-on; public HTTPS for the required demo URL). Fly.io documented as alternative. Local dev via Docker Compose.

---

## 6. Security, privacy & trust
- RBAC + per-object authz (BOLA #1) on every fetch; RLS backstop on career-history/applications/consent.
- Consent enforced at the repository layer (queries filter by active `ConsentGrant`).
- Append-only audit log for all sensitive access; data export + erasure endpoints.
- Rate limiting (slowapi/Redis), CORS allowlist, security headers, secrets via env/Key Vault.
- PDPA (Malaysia) + GDPR: explicit/granular/revocable consent, data minimization, documented retention, encryption at rest (Neon default).
- **AI provenance manifest** in `docs/` and surfaced in-app.

---

## 7. Tech stack (summary)
**Backend:** Python 3.12, FastAPI, async SQLAlchemy 2.0, Pydantic v2 + pydantic-settings, Alembic, asyncpg, pgvector, ARQ, Redis, Argon2 (argon2-cffi), python-jose/PyJWT, tenacity, structlog, slowapi, openai SDK (Azure), pytest + httpx + testcontainers + polyfactory.
**Frontend:** React 18, Vite, TypeScript, TanStack Query, TanStack Router, Zustand, Tailwind, shadcn/ui (Radix), react-hook-form, zod, Recharts, Vitest + Testing Library.
**Infra:** Docker, Docker Compose, GitHub Actions (lint/type-check/test), Vercel + Render + Neon.
**Data:** O*NET (CC-BY), ESCO v1.2, Lightcast Open Skills (taxonomy), OpenDOSM wages, UN World Population Prospects 2024, W3C VC / Open Badges 3.0.

---

## 8. Build phasing & maturity matrix

| Phase | Scope | Tiers |
|---|---|---|
| **P0 — Foundation** | Monorepo, CI, Docker Compose, DB + migrations, auth + RBAC, Career Graph schema, taxonomy seed, LLMClient + Azure, seed data pipeline | Tier A |
| **P1 — Core jobsite** | Profiles, résumé parsing, jobs, hybrid search, applications, dashboards, matching + Glass Box | Tier A |
| **P2 — Signature AI** | Trajectory Atlas, Career Copilot, Fair Pay Engine, Career Weather, Pivot Feasibility | Tier A |
| **P3 — Employer & University depth** | Smart Matching, Bias Auditor, Retention Signals, Adaptive Readiness, Outcome Loop, Internship Marketplace | Tier A/B |
| **P4 — Breadth modules** | Living Portfolio, Life Chapter Designer, Re-Engagement, Onboarding Predictor, Curriculum Engine, Workforce Resilience, Learning Wallet | Tier B/C |
| **P5 — Admin, polish, hardening** | Mission Control, i18n, a11y, perf, security pass, tests, docs, demo script | Tier A |

The README ships an **honest maturity matrix** (A/B/C per feature). Honesty is scored.

---

## 9. Intent Form deliverables (due 2026-06-15)
- **Concept brief (~800 words)** — built from §1–§3.
- **Supporting one-pager / deck outline** — vision, three control rooms, signature screens, architecture diagram.
- **Live demo URL** — the working core (P0–P1+), doubling as the "clickable prototype."
- Team-identity fields (names, phones, teammates, LinkedIn/GitHub) left as fill-ins for the user.

---

## 10. Testing & quality
- Backend: pytest + pytest-asyncio + httpx ASGI; testcontainers Postgres (real pgvector); polyfactory fixtures; **LLMClient mocked** (never call Azure in tests); explicit RBAC + tenant-isolation + consent tests.
- Frontend: Vitest + Testing Library; critical-path component tests.
- CI: ruff + mypy + pytest (backend); eslint + tsc + vitest (frontend).
- Conventional commits; clean README + architecture + API docs + AI provenance + runbook.

---

## 11. Risks & mitigations
- **Scope vs. time** → tiering + honest maturity matrix; Tier A is the demo spine.
- **Azure cost/latency** → caching, token caps, usage ledger, mocked tests.
- **Hallucination / false precision** → structured outputs with citations + confidence; refuse-to-fabricate guardrail; ranges not answers.
- **Data licensing** → open data + synthetic seed only; commercial feeds are documented integration points.
- **Privacy of sensitive career data** → consent-at-repository, RLS, audit, export/erasure.

---

## 12. Success criteria (mapped to the rubric)
- **Product & UX (30%)** — the longitudinal Career Graph thesis, four coherent control rooms, ranges + Glass Box, real personas.
- **System Design (25%)** — one graph, many lenses; clean domain boundaries; swappable AI; integration points.
- **Completeness (20%)** — end-to-end Tier A, live demo URL, honest maturity matrix, Dockerized + deployable.
- **AI Craft (15%)** — Azure OpenAI behind an abstraction, structured outputs, RAG, guardrails, provenance manifest.
- **Code Quality (10%)** — domain structure, naming, docs, security, tests; reads cleanly to a stranger.
