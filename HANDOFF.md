# Atlas — Session Handoff & End-to-End Context

> Read this first if you're a new agent (or human) picking up this repo.
> It captures **what Atlas is, what's live, how it was built, every non-obvious
> decision, the gotchas that will bite you, and what's next.** Operational
> commands/conventions live in [AGENTS.md](AGENTS.md); Claude-Code-specific rules
> in [CLAUDE.md](CLAUDE.md).

---

## 1. TL;DR — current state (2026-06-15)

**Atlas — Asia's Career OS.** One candidate-owned *Career Graph* seen through three
connected control rooms (candidates / employers / universities) + an admin console.
Built for the **Talentbank Tech Hackathon, First Cohort 2026**.

**It is built, deployed, and verified end-to-end:**
- **Live app (public):** https://frontend-bay-two-7untyz4smg.vercel.app
- **Pitch deck (public):** https://frontend-bay-two-7untyz4smg.vercel.app/deck.html
- **Backend API:** https://atlas-api-w4mm.onrender.com (`/health`, `/docs`)
- **Repo:** https://github.com/Vishwa-docs/atlas-career-os (private, branch `main`)
- Stack chain: **Vercel (React) → Render (FastAPI) → Neon (Postgres+pgvector) → Azure OpenAI GPT-4o**
- 62 API routes · 35 frontend pages (0 crashes) · 30 backend tests passing · ruff + tsc clean
- Demo logins (password `demo1234`): `aisyah@demo.atlas` (candidate), `daniel@demo.atlas`
  (employer), `dr.tan@demo.atlas` (university), `admin@demo.atlas` (admin). The login page
  has **one-click demo buttons** (no password needed).

---

## 2. What Atlas is (the thesis)

Careers in Asia are built alone, in the dark. Job boards see jobs, ATS sees filters,
universities see graduation — **nobody sees a career as one continuous 40-year thing.**
Atlas changes the unit of analysis from the *transaction* to the *trajectory*: a portable,
candidate-owned **Career Graph** that all three sides read.

Two non-negotiable product principles (from Ben Ho's brief):
1. **A map, not a fortune-teller** — show realistic *ranges* of outcomes, never one prediction.
2. **No black-box scores** — every AI judgement ships a **Glass Box**: plain-language
   rationale + cited evidence + a confidence band + "what would change this."

The three audiences + their signature modules are mapped in
[docs/architecture/overview.md](docs/architecture/overview.md) and the deck.

---

## 3. Live deployment & accounts

| Layer | Where | Notes |
|---|---|---|
| Frontend | **Vercel** (scope `jackbrights-projects`) | prod alias `frontend-bay-two-7untyz4smg.vercel.app`. Build needs `VITE_API_BASE_URL`. |
| Backend | **Render** free web service `atlas-api` | `render.yaml` = single free service (no Redis/worker). Binds `$PORT`. Spins down after ~15 min idle (≈50s cold start). |
| Database | **Neon** (ap-southeast-1) | Provisioned + seeded already. `DB_REQUIRE_SSL=true`. Use the **direct** (non-pooled) endpoint. |
| AI | **Azure OpenAI** | deployment `gpt-4o-2`, api version `2024-12-01-preview`, endpoint = resource base (no `/openai/...` path). Key is in `backend/.env` (gitignored) + Render env. |
| Git | **GitHub** `Vishwa-docs/atlas-career-os` | private. `gh` is authed as `Vishwa-docs`. |

To re-point the frontend at a different backend: redeploy with
`cd frontend && npx vercel --prod --yes --build-env VITE_API_BASE_URL=<api>/api/v1`,
and add the Vercel origin to the backend's `CORS_ORIGINS`.

Full deploy runbook: [docs/DEPLOY.md](docs/DEPLOY.md).

---

## 4. Run it locally (fast path)

```bash
docker compose up          # db(pgvector)+redis+api(:8000)+worker+frontend(:5173)
```
Or split (backend venv is **Python 3.12**, system python is 3.9 — always use the venv/Docker):
```bash
docker compose up -d db redis
cd backend && cp .env.example .env   # then edit; or it already exists locally
.venv/bin/python -m app.scripts.init_db && .venv/bin/python -m app.scripts.seed
.venv/bin/python -m uvicorn app.main:app --port 8000
cd ../frontend && npm install && npm run dev
```
`USE_MOCK_LLM=true` (default) runs the whole app with a deterministic mock — no Azure key
needed, hermetic tests. Set `USE_MOCK_LLM=false` + the `AZURE_*` vars for real AI.

---

## 5. Architecture map (where things live)

**Backend** `backend/app/` — FastAPI, domain-sliced. Each `domains/<x>/` has
`router.py` (thin) → `service.py` (logic, authz, commits) → `repository.py` (all SQL) →
`models.py` / `schemas.py`. 17 domains:
`auth, users, candidates, employers, universities, jobs, applications, matching,
taxonomy, signals, consent, credentials, notifications, admin, ai, organizations`.
- Shared core: `app/core/` (config, db, security, deps/RBAC, exceptions, schemas, roles, logging).
- AI subsystem: `app/domains/ai/` — `llm/` (client Protocol, azure, mock, composite, resilient,
  factory), `guardrails.py`, `schemas.py` (Glass Box), `rag/`, `prompts/`, feature services.
- Routers auto-mount in `app/api/v1/router.py`; models auto-discover in `app/db/registry.py`.

**Frontend** `frontend/src/` — React + Vite + TanStack Query + Tailwind/shadcn.
- `app/` shell: `router.tsx`, `AppShell.tsx`, `RequireAuth.tsx`, `nav.ts`, `tourSteps.ts`, `theme.tsx`, `providers.tsx`.
- `features/<persona>/` — `candidate`, `employer`, `university`, `admin`, `auth`, `marketing`,
  `notifications`. Each has `pages/` + `api.ts` (TanStack Query hooks).
- `lib/` — `apiClient.ts` (typed fetch + token refresh), `sse.ts` (streaming), `tokenStore.ts`, `utils.ts`.
- `components/ui/` — shadcn-style primitives; `components/guided-tour.tsx` (Qtips); design tokens in `index.css`.
- Static pitch deck: `frontend/public/deck.html` (served at `/deck.html`).

**Data spine** (the Career Graph): skills/occupations standardized via **O*NET / ESCO /
MASCO bridged through ISCO-08**; **DOSM** wages anchor Fair Pay; **UN WPP** for Workforce
Resilience; **W3C VC / Open Badges 3.0** for the Learning Wallet. Seeded by `app/scripts/seed.py`.

---

## 6. Skills & tools used this session

- **`superpowers:brainstorming`** — locked the concept + system design before building (the design spec is committed: [docs/superpowers/specs/2026-06-14-atlas-career-os-design.md](docs/superpowers/specs/2026-06-14-atlas-career-os-design.md)).
- **`Workflow` tool (ultracode)** — two big fan-outs: (a) the initial 15-agent parallel build of backend domains + frontend workspaces; (b) a 4-agent parallel **crash-fix** that reconciled frontend↔backend API shapes.
- **`Agent` tool** — 3 parallel research agents (see §7); a shape-reconciliation agent.
- **`frontend-slides:frontend-slides`** — generated the 23-slide `deck.html`.
- **Claude Preview** (`preview_*`) — drove the local UI for verification (note: sandboxed to localhost).
- **Playwright** (installed `--no-save`, not in `package.json`) — captured `screenshots/` and verified the **public** site end-to-end (login + streaming AI).
- **Azure OpenAI** (GPT-4o) — the live model behind all AI features.

---

## 7. Research done + key findings

Three parallel research agents (web) informed the design:
1. **Competitive landscape** → the white space is the **longitudinal, portable, tri-sided**
   layer. LinkedIn/Indeed/Mercor are episodic; Gloat/Eightfold/Fuel50 are enterprise-locked;
   Handshake abandons students at graduation. A candidate-owned lifelong graph is unoccupied.
2. **AI/data techniques + open sources** → O*NET (CC-BY), ESCO, Lightcast Open Skills,
   **ISCO-08 as the pivot to Malaysia's MASCO**; **OpenDOSM** wages; **UN WPP 2024** demographics;
   **W3C VC / Open Badges 3.0** credentials; pgvector **hybrid search (BM25 + vector via RRF)**;
   LLM **structured-output** resume parsing; transition-graph / CAREER-style trajectory modeling.
3. **Production architecture** → FastAPI domain modules + async SQLAlchemy 2.0, ARQ, RAG over
   Azure OpenAI with a swappable client, RBAC + row-level security, audit + cost ledger.

---

## 8. Key decisions & rationale

1. **Stack: FastAPI + React (not Next.js/Java).** User choice; clean API/SPA split, Python's
   data ecosystem for the AI/graph work.
2. **All three audiences over one shared graph** (not one persona). The shared graph *is* the moat.
3. **Glass Box as a platform-wide contract**, not a feature — directly answers "no black-box scores."
4. **Swappable `LLMClient` Protocol.** Nothing calls Azure directly. Enables the mock (hermetic
   tests, offline demo) and the resilient/composite wrappers.
5. **Composite LLM client (live mode): real Azure for generative calls + deterministic embedder
   for vectors.** The seeded corpus was embedded with the deterministic embedder, so query
   vectors MUST come from the same embedder or semantic search breaks. (`USE_AZURE_EMBEDDINGS=false`.)
6. **Resilient LLM client:** Azure → deterministic fallback on any failure, so AI is never blank.
7. **Hosting: Vercel + Render(free) + Neon** — all free/cardless. Render Redis is paid, so we
   dropped Redis + the worker (the API needs neither; WS notifications use an in-process manager).
8. **Deterministic mock + real Postgres in tests** (testcontainers pgvector) — pgvector/RLS/JSONB
   behave exactly as prod; no paid API calls in CI.

---

## 9. Known gotchas & fixes applied (READ BEFORE TOUCHING THESE)

1. **Azure jailbreak content-filter.** Our original anti-prompt-injection wording
   (`<untrusted_content>` fences, "never follow instructions") tripped Azure's *jailbreak*
   filter → HTTP 400 → blank AI everywhere. **Fixed** in `domains/ai/guardrails.py` by rewording
   to neutral data-delimiting. **Do NOT reintroduce adversarial "untrusted/ignore instructions"
   phrasing into prompts.** Backstop: `ResilientLLMClient` falls back to the mock on any 400.
2. **Embeddings must stay deterministic** (see decision #5). Don't flip `USE_AZURE_EMBEDDINGS`
   without re-embedding the whole corpus with Azure.
3. **Azure config specifics:** deployment is **`gpt-4o-2`** (not `gpt-4o`), api version
   `2024-12-01-preview`, endpoint = the resource base only (`https://….cognitiveservices.azure.com`,
   strip the `/openai/deployments/...` path).
4. **Neon:** requires SSL → `DB_REQUIRE_SSL=true` (sets asyncpg `ssl=require`). `config.py`
   auto-strips `sslmode`/`channel_binding` query params so a raw Neon URL pastes in fine. Use the
   **direct** (non-pooled) endpoint — the pooler + asyncpg prepared statements conflict.
5. **Render free tier:** no `preDeployCommand`; the container must bind **`$PORT`** (Dockerfile
   CMD does `--port ${PORT:-8000}`); spins down when idle (~50s cold start). Don't add paid services
   to `render.yaml`.
6. **Parallel-build API-shape drift:** the initial fan-out left 9 pages crashing on
   frontend/backend shape mismatches (e.g. dashboard `stats` object vs array). **Fixed.** Rule:
   the **backend response is the source of truth**; adapt the frontend in the TanStack Query `select`.
7. **Verification reality:** the Preview tool is **sandboxed to localhost** (can't open the Vercel
   URL); `preview_screenshot` **hangs** on animated / WebSocket-connected pages (use
   `preview_snapshot` for text, or Playwright `--no-save` for screenshots + external sites).
   **Token-injection login bypassed the real UI and hid the jailbreak bug — always test AI by
   actually clicking through the UI.**
8. **Python:** system `python3` is 3.9; the project targets 3.11+/3.12. Always use
   `backend/.venv/bin/python` or Docker — never system python for the app.

---

## 10. Maturity tiers (be honest in any demo/submission)

- **Tier A (deep, production-shaped):** auth/RBAC, Career Graph + taxonomy, hybrid search +
  trajectory matching, Trajectory Atlas, Career Copilot (streaming), Fair Pay, candidate/employer/
  university/admin dashboards, Consent Center, Glass Box, CV/PDF export, realtime notifications.
- **Tier B (functional, lighter):** Retention Signals, Re-Engagement, Onboarding Predictor,
  Living Portfolio, Life Chapters, Internship Marketplace, Curriculum Engine, Workforce Resilience,
  Adaptive Readiness, Career Weather, Bias Auditor.
- **Tier C (scaffolded):** Lifelong Learning Wallet credentials, deeper longitudinal analytics.

Tiers are surfaced in the sidebar (the `tier` badge in `nav.ts`).

---

## 11. What's next (28-day build phase: 29 Jun – 26 Jul 2026)

- Deepen **Tier C → B/A**: Learning Wallet (issue/verify VCs), longitudinal cohort analytics.
- Re-introduce the **ARQ worker + a queue** on a host that allows it (or a cron) for re-embedding,
  retention-signal computation, and digest notifications.
- **Alembic migrations** instead of `create_all` once the schema stabilizes (env is wired in `alembic/`).
- Real data integrations: live job-posting ingestion, DOSM wage refresh, O*NET/ESCO import jobs.
- Harden: rate-limit tuning, e2e test coverage of AI UI flows, observability.
- Optional: move the Vercel project under the user's own `vishwa-docs` scope; warm-keep the Render service.

---

## 12. Files to read (doc index)

| File | What |
|---|---|
| [AGENTS.md](AGENTS.md) | Build/run/test/deploy + code conventions (tool-agnostic) |
| [CLAUDE.md](CLAUDE.md) | Claude-Code-specific golden rules + commands |
| [README.md](README.md) | Public-facing project overview |
| [docs/architecture/overview.md](docs/architecture/overview.md) | System + module overview |
| [docs/architecture/api-contract.md](docs/architecture/api-contract.md) | API conventions (Page, errors, auth) |
| [docs/superpowers/specs/2026-06-14-atlas-career-os-design.md](docs/superpowers/specs/2026-06-14-atlas-career-os-design.md) | The approved design spec (the "why") |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Neon → Render → Vercel runbook (+ Azure alt) |
| [docs/DEMO.md](docs/DEMO.md) | Video demo script (scene-by-scene) |
| [docs/ai-provenance.md](docs/ai-provenance.md) | AI tooling + provenance disclosure |
| [docs/intent-form-brief.md](docs/intent-form-brief.md) | Hackathon Intent Form concept brief |
| `screenshots/` | 20 captured pages + deck slides (for Drive / supporting materials) |

When in doubt about *behaviour*, the backend is the source of truth — read the relevant
`domains/<x>/service.py` and `schemas.py`.
