# AGENTS.md — Atlas build, run & conventions

Operational manual for any agent/tool working in this repo (Claude Code, Codex, Cursor,
Gemini, etc.). For the *story* (decisions, research, deploy state, gotchas) read
[HANDOFF.md](HANDOFF.md) first. Claude-Code-specific rules: [CLAUDE.md](CLAUDE.md).

Atlas — Asia's Career OS. Monorepo: `backend/` (FastAPI) + `frontend/` (React/Vite),
`render.yaml` (backend deploy), `docker-compose.yml` (local), `docs/`.

---

## Prerequisites

- **Docker** (for local Postgres+Redis and the backend test-suite's testcontainers).
- **Node 22** for the frontend.
- **Python 3.11+** for the backend. ⚠️ The machine's system `python3` is **3.9** — do NOT
  use it for the app. Use `backend/.venv/bin/python` (Python 3.12) or Docker.

---

## Project layout

```
backend/                 FastAPI service
  app/
    core/                config, db (async engine), security, deps (RBAC), exceptions, schemas, roles, logging
    api/v1/router.py     auto-mounts every domains/<x>/router.py
    db/                  base (DeclarativeBase + mixins), registry (auto-imports models)
    domains/<x>/         router.py → service.py → repository.py + models.py + schemas.py
    domains/ai/          llm/{client,azure,mock,composite,resilient,factory}, guardrails, schemas (Glass Box), rag/, prompts/
    workers/             ARQ tasks (NOT deployed on the free tier)
    scripts/             init_db.py, seed.py
  alembic/               migrations env (currently using create_all; migrations are the next step)
  tests/                 pytest (real pgvector via testcontainers, deterministic mock LLM)
  pyproject.toml         deps + ruff/mypy/pytest config
  Dockerfile             python:3.12-slim; CMD binds $PORT
frontend/                React + Vite + TanStack Query + Tailwind/shadcn
  src/app/               router, AppShell, RequireAuth, nav, tourSteps, theme, providers
  src/features/<x>/      pages/ + api.ts (one persona per dir)
  src/lib/               apiClient, sse, tokenStore, utils
  src/components/ui/     shadcn-style primitives; guided-tour.tsx
  public/deck.html       static 23-slide pitch deck (served at /deck.html)
  vercel.json            Vite build + SPA rewrite
docker-compose.yml       db(pgvector)+redis+api+worker+frontend
render.yaml              SINGLE free Render web service (no Redis/worker)
```

---

## Run

```bash
# Everything in Docker
docker compose up                       # frontend :5173, api :8000/docs

# Or split:
docker compose up -d db redis
cd backend && .venv/bin/python -m app.scripts.init_db    # schema + pgvector (idempotent)
              .venv/bin/python -m app.scripts.seed        # demo data (--if-empty to skip if seeded)
              .venv/bin/python -m uvicorn app.main:app --port 8000
cd frontend && npm install && npm run dev                 # :5173 (proxies /api -> :8000, ws:true)
```

Demo logins (password `demo1234`): `aisyah@demo.atlas`, `daniel@demo.atlas`,
`dr.tan@demo.atlas`, `admin@demo.atlas`. Login page also has one-click demo buttons.

---

## Test / lint / typecheck

```bash
# Backend (needs Docker running for testcontainers Postgres)
cd backend
.venv/bin/python -m pytest -q          # 30 tests, deterministic mock LLM, no paid API calls
.venv/bin/ruff check app               # lint (config in pyproject.toml)
.venv/bin/ruff format app              # format

# Frontend
cd frontend
npm run typecheck                      # tsc --noEmit (must be clean)
npm run lint                           # eslint
npm run build                          # tsc + vite build (what Vercel runs)
npm run test                           # vitest
```
CI: `.github/workflows/ci.yml` runs all of the above.

---

## Backend conventions (follow these exactly)

- **Layering per domain:** `router.py` is thin (no SQL, no business logic) → `service.py` owns
  business logic, **authorization (BOLA per-object checks)**, and the **`session.commit()`**
  boundary → `repository.py` owns **all** SQLAlchemy queries (async `select()`).
- **Async SQLAlchemy 2.0** (`Mapped[...]`, `mapped_column`). UUID primary keys. Models inherit
  `Base` + `UUIDMixin`/`TimestampMixin` from `app/db/base.py`. New `models.py` files are
  auto-discovered (`app/db/registry.py`) — no central registry edit needed.
- **Errors:** raise semantic exceptions from `app/core/exceptions.py` (`NotFoundError`,
  `ForbiddenError`, `ConflictError`, `ConsentRequiredError`, …). A single handler maps them to
  `{"error":{"code","message"}}`. Don't raise raw `HTTPException` in services.
- **Auth/RBAC:** `Depends(get_current_principal)` for the actor; `Depends(require_roles(...))` to
  guard. Roles in `app/core/roles.py`. Org-scoped access uses `require_same_org` + Postgres RLS.
- **Pagination:** return `Page[T]` built from `PageParams` (`app/core/schemas.py`).
- **AI:** never call the Azure SDK directly — depend on the `LLMClient` via
  `Depends(get_llm)` / `get_llm()`. Every AI output embeds a **`GlassBox`**
  (`app/domains/ai/schemas.py`): rationale + citations + confidence + what-would-change-it.
  Wrap untrusted text with `guardrails.wrap_untrusted` (benign wording — see gotcha #1 in HANDOFF).
  Record spend with `ai.usage.record_usage`.
- **Cross-domain calls** (e.g. `notifications.create_notification`) are wrapped in `try/except` so
  one domain failing never breaks another.

## Frontend conventions

- **Feature-sliced:** one dir per persona under `features/`. Data access lives in that dir's
  `api.ts` as **TanStack Query** hooks calling `lib/apiClient`. Never `fetch` Azure or build URLs ad hoc.
- **API shape = backend.** When backend & frontend disagree, fix the frontend in the query
  `select` to match the backend response (backend is source of truth).
- **UI:** compose `components/ui/*` (shadcn-style). Theme via CSS variables in `index.css`
  (the "Midnight & Aurora" tokens). Use the `cn()` util. Streaming via `lib/sse.ts`.
- **Routing:** add a lazy import + `<Route>` in `app/router.tsx` and a nav entry in `app/nav.ts`
  (with a `tier` badge A/B/C). Auth gating via `RequireAuth`.

---

## Environment variables (backend `.env`, gitignored)

| Var | Local | Prod (Render) |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://atlas:atlas@localhost:5432/atlas` | Neon URL (raw or async; query params auto-stripped) |
| `DB_REQUIRE_SSL` | `false` | `true` |
| `USE_MOCK_LLM` | `true` (offline) or `false` | `false` |
| `USE_AZURE_EMBEDDINGS` | `false` | `false` (keep deterministic embeddings) |
| `AZURE_OPENAI_ENDPOINT` | resource base URL | same |
| `AZURE_OPENAI_API_KEY` | — | (secret) |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4o-2` | `gpt-4o-2` |
| `AZURE_OPENAI_API_VERSION` | `2024-12-01-preview` | same |
| `CORS_ORIGINS` | `http://localhost:5173` | the Vercel URL |
| `SECRET_KEY` | dev value | generated |

`.env.example` documents the contract. **Never commit `.env` or any secret.**

---

## Deploy (summary — full runbook in docs/DEPLOY.md)

- **DB:** Neon (already provisioned). Direct endpoint; SSL via `DB_REQUIRE_SSL=true`.
- **Backend:** Render Blueprint reads `render.yaml` → one free Docker web service. Set the
  `sync:false` env vars (`DATABASE_URL`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`,
  `CORS_ORIGINS`). No `preDeployCommand` (free-tier limitation; DB is pre-provisioned).
- **Frontend:** `cd frontend && npx vercel --prod --yes --build-env VITE_API_BASE_URL=<api>/api/v1`.
  Then ensure the Vercel origin is in the backend `CORS_ORIGINS`.

---

## Hard rules

1. Never commit secrets / `.env`. Verify with `git check-ignore backend/.env` before pushing.
2. Never call the Azure SDK outside `domains/ai/llm/azure.py` — go through `LLMClient`.
3. Don't reintroduce adversarial anti-injection wording into prompts (Azure jailbreak filter).
4. Don't enable `USE_AZURE_EMBEDDINGS` without re-embedding the corpus.
5. Backend is the source of truth for API shapes; adapt the frontend, not the contract, unless changing both deliberately.
6. Use the venv/Docker (Python 3.12), never system `python3` (3.9).
7. Commit/push only when asked; end commit messages with the project's `Co-Authored-By` line.
