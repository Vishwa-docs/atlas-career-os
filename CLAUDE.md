# CLAUDE.md — Claude Code operating guide for Atlas

**Start here, then read [HANDOFF.md](HANDOFF.md) (full context: decisions, research, deploy
state, gotchas) and [AGENTS.md](AGENTS.md) (build/run/conventions).** Don't re-derive what
those already document.

Atlas — Asia's Career OS (Talentbank Tech Hackathon 2026). Monorepo: `backend/` FastAPI +
`frontend/` React/Vite. **It is built, deployed, and live** — see HANDOFF §1 for URLs.

---

## Golden rules (the ones that bite)

1. **AI prompts must stay benign.** Azure's content filter flags anti-injection wording
   (`untrusted_content`, "never follow instructions") as a *jailbreak* → HTTP 400 → blank AI.
   Keep `domains/ai/guardrails.py` neutral. The `ResilientLLMClient` is the backstop. (HANDOFF §9.1)
2. **Never call Azure directly.** Everything goes through the `LLMClient` Protocol
   (`Depends(get_llm)`). Every AI output carries a **Glass Box** (rationale + citations +
   confidence + what-would-change-it).
3. **Embeddings stay deterministic** (`USE_AZURE_EMBEDDINGS=false`). The seeded corpus was
   embedded with the deterministic embedder; mixing embedders breaks semantic search. (HANDOFF §9.2)
4. **Backend is the source of truth** for API shapes. When a page breaks on a shape mismatch,
   fix the frontend in the TanStack Query `select`, not the contract.
5. **Use the venv (Python 3.12), never system `python3` (3.9).** Run via `backend/.venv/bin/python`
   or Docker.
6. **Never commit `.env` / secrets.** Verify `git check-ignore backend/.env`. Commit/push only
   when the user asks; end commit messages with:
   `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
7. **Test AI by actually clicking the UI**, not by injecting tokens — token-injection hid a
   real jailbreak bug once. Drive the real login + AI flows.

---

## Most-used commands

```bash
# Run
docker compose up                                         # full stack (fe :5173, api :8000)
cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000   # api only (venv)
cd frontend && npm run dev                                # frontend only

# Verify
cd backend && .venv/bin/python -m pytest -q && .venv/bin/ruff check app   # 30 tests + lint
cd frontend && npm run typecheck && npm run build         # tsc + vite build
cd backend && .venv/bin/python -c "from app.main import app; print(len(app.openapi()['paths']))"  # route count

# DB
cd backend && .venv/bin/python -m app.scripts.init_db     # schema + pgvector (idempotent)
              .venv/bin/python -m app.scripts.seed         # demo data
curl -s localhost:8000/health                             # {"status":"ok","llm":"azure|mock"}
```

---

## Verification notes specific to this environment

- **Claude Preview is sandboxed to localhost** — it can't open the public Vercel URL. To test the
  deployed site, use Playwright (install `--no-save`: `npm i --no-save playwright && npx playwright
  install chromium`) — see how `screenshots/` were captured (HANDOFF §6).
- **`preview_screenshot` hangs on animated / WebSocket-connected pages** (the landing, the app
  shell with the realtime bell, the deck). Use `preview_snapshot` (a11y tree, text proof) for the
  app, and Playwright for real screenshots. SVG/animated pages: capture a public/static route or
  use Playwright with a fixed wait, not network-idle.
- Restarting the backend: kill cleanly (`lsof -ti:8000 | xargs kill -9; pkill -f "uvicorn app.main"`)
  — stale duplicate processes have caused mismatched `/health` (`mock` vs `azure`).

---

## Workflows & subagents

- This project was built with the **Workflow** tool (parallel fan-out) and the **Agent** tool. When
  fanning out a build/fix across the repo, give one agent per **domain** (disjoint files) — shared
  files like `features/<x>/api.ts`, `app/router.tsx`, `app/nav.ts` must be owned by a single agent
  to avoid conflicts.
- After any parallel edit, re-verify: `pytest`, `tsc --noEmit`, and click through the affected pages.

## Skills

The `superpowers` skills are available (use `brainstorming` before new creative work,
`writing-plans`/`executing-plans` for multi-step builds). `frontend-slides` generated
`frontend/public/deck.html`. Invoke skills via the Skill tool; only use ones listed in the
session's available-skills reminders.

---

## When the user asks for...

- **"deploy" / "make it live":** the chain is Vercel + Render(free) + Neon — see [docs/DEPLOY.md](docs/DEPLOY.md). Backend on Render free = single web service, no Redis, binds `$PORT`, no preDeploy.
- **"the AI isn't working":** check `/health` shows `llm:azure`, then check Azure isn't content-filtering (HANDOFF §9.1); the resilient client should fall back to mock, never blank.
- **"intent form / brief / deck":** see [docs/intent-form-brief.md](docs/intent-form-brief.md) and `frontend/public/deck.html`.
- **demo script:** [docs/DEMO.md](docs/DEMO.md).
