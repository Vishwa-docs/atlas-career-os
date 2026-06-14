# AI Provenance Declaration

**Project:** Atlas — Asia's Career OS
**Event:** Talentbank Tech Hackathon (First Cohort)
**Last updated:** 2026-06-14

This document is Atlas's honest declaration of **which AI was used, where, and how it is kept
safe and accountable** — per the hackathon rules and per our own "Glass Box, never black box"
commitment. It covers both AI used to *build* Atlas and AI that runs *inside the product*.

---

## 1. Models & tools used

### In-product (runtime) AI
| Purpose | Model / tool | Notes |
|---|---|---|
| Chat, reasoning, structured verdicts | **Azure OpenAI — gpt-4o-class** chat deployment | Configured via `AZURE_OPENAI_DEPLOYMENT` (default `gpt-4o`). |
| Embeddings (semantic search, RAG, matching) | **Azure OpenAI — text-embedding-3-large** | Dimensions trimmed to `EMBEDDING_DIMENSIONS` (default 1536) for storage in pgvector. |
| Offline / test / CI execution | **`MockLLMClient`** (deterministic, in-repo) | No network, no keys; produces stable, schema-valid Glass Box outputs so every feature is demoable offline. |

Both production models sit **behind a single `LLMClient` Protocol**
(`backend/app/domains/ai/llm/client.py`). Application code never calls the Azure SDK directly —
it depends on the Protocol, so the provider is swappable and the mock can be injected in tests.
The live Azure client is only selected when `USE_MOCK_LLM=false` **and** Azure credentials are
present; otherwise Atlas logs a warning and falls back to the mock.

### Build-time AI
- **Claude Code** (Anthropic) was used as an engineering assistant to help design, scaffold,
  and document this codebase. All output was reviewed by the team, which retains ownership of
  the code (see the README's ownership note).

No other AI services are called at runtime. No customer/candidate data is sent to any model
provider other than Azure OpenAI, and only when live mode is explicitly enabled.

---

## 2. Where AI is used in the product

Every item below returns a **Glass Box** payload (rationale + citations + confidence band +
"what would change this" + caveats) and is metered into the per-org cost ledger.

| Surface | Endpoint | What the AI does |
|---|---|---|
| **Résumé parsing** | `POST /candidates/me/resume/parse` | Parses an uploaded résumé into a structured graph (roles, skills, education) — schema-first, grounded, with a confidence flag per inference. Does **not** auto-commit; the user confirms. |
| **Match explanations** | `GET /jobs/{id}/match`, `GET /matching/jobs`, `GET /matching/candidates` | Explains a trajectory-aware fit score with sub-scores (semantic, skill overlap, trajectory fit, salary fit) and citations. |
| **Career Copilot** | `POST /ai/coach`, `POST /ai/coach/stream` (SSE) | Streaming career coach; reasons over the user's graph + market data via tool-use; cites sources; surfaces uncertainty. |
| **Trajectory Atlas** | `POST /ai/atlas` | Generates realistic next-move routes with salary ranges, time bands, feasibility, skill gaps, and trade-offs. |
| **Fair Pay Engine** | `POST /ai/fair-pay` | DOSM-anchored market range (P25/P50/P75) for role/region/experience, plus negotiation timing and script. |
| **Career Weather** | `POST /ai/weather` | Plain-language local market briefing: demand index, rising/cooling skills, salary drift. |
| **Pivot Feasibility** | `POST /ai/pivot` | Gap analysis + a realistic learning ramp for a target occupation. |
| **Adaptive Readiness** | `GET /universities/students/{id}/readiness` | Live employability signal with explained dimensions. |
| **Curriculum Engine** | `GET /universities/curriculum` | Forward-projects market-vs-program skill gaps for faculty. |
| **Bias Auditor (debias)** | `POST /jobs/{id}/debias` | Rewrites job-description language to reduce bias, flagging each issue with a reason and suggestion. |
| **Workforce scenarios** | `GET /employers/workforce` | UN-WPP-based demographic projections and hire/retain/AI/migrate scenarios. |

---

## 3. Prompt-design approach

- **System preamble.** Every call is anchored by a shared preamble (see
  `backend/app/domains/ai/guardrails.py`) that defines Atlas as a *career navigation co-pilot,
  not a predictor*, and mandates: explain reasoning in plain language, cite evidence, state
  confidence and what would change the view, prefer honest ranges over false precision, and
  never invent facts.
- **Structured outputs.** AI verdicts are produced via constrained decoding into Pydantic
  models, so every response is a validated object carrying `rationale`, `citations[]`, and a
  `confidence` band. The React UI renders these through one shared **Glass Box** component — so
  explainability is structural, not best-effort prose.
- **Grounding / RAG.** Answers are grounded in retrieved context — the user's career graph, the
  job corpus, and market data — using structure-aware chunking, hybrid retrieval
  (pgvector + keyword) fused with Reciprocal Rank Fusion, with optional rerank of the top hits.
- **Ranges + confidence + citations.** Outputs surface a *spread* with trade-offs and explicit
  citations, never a single false-precise number.

---

## 4. Guardrails

- **Prompt-injection delimiting.** All untrusted text (résumés, job descriptions, retrieved
  chunks) is fenced in `<untrusted_content>` tags via `wrap_untrusted()`, with an explicit
  instruction that nothing inside may alter the model's instructions. Closing-tag injection is
  stripped. Retrieved text is treated strictly as data.
- **PII redaction before logging.** `redact_pii()` masks emails and phone numbers before any
  log line is written. (It is a logging-safety measure, not a security boundary.)
- **Refuse to fabricate.** The preamble forbids inventing employers, salaries, or skills not
  supported by context; when unsure, the model is told to say so. Confidence bands make
  uncertainty visible rather than hidden.
- **Cost ledger & budgets.** Every AI call records token usage attributable to the org/user in
  an `llm_usage` ledger, surfaced in Mission Control's AI usage dashboard; per-request token
  caps and tenacity retries (honoring `Retry-After`) bound cost and latency.
- **Consent-gated context.** When AI reasons over another person's graph (e.g. employer-side
  matching), the underlying data access is filtered by active consent grants — the model never
  sees ungranted candidate data.

---

## 5. Honesty stance

Atlas is **a map, not a fortune-teller.** We deliberately refuse the things that make AI
career products untrustworthy: naked scores, single-number predictions, and black-box verdicts.
Where a feature is shallower than its production vision, it is **labeled Tier B/C in the
README's maturity matrix** rather than dressed up. The deterministic mock means reviewers can
exercise every AI surface without keys — and what they see offline is the same shape of output
the live model returns, just without live grounding. We would rather show a smaller honest
system than a larger one that bluffs.
