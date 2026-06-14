# Talentbank Intent Form — Atlas: Asia's Career OS

## Concept brief

**Atlas is Asia's Career OS: one portable, candidate-owned Career Graph, seen through three
control rooms — a map, not a fortune-teller.**

Careers today are built spontaneously, unpredictably, and alone. The systems sitting between
people and opportunity were never built to see the whole picture: job boards see *this* job, an
ATS sees filters, a university sees graduation. Nobody sees a career as one continuous, 40-year
thing. The gap is structural, not incremental — trackers go dormant once you're hired,
enterprise skills graphs only work inside 1,000+-employee firms, and APAC has no continuous
navigator at all. Atlas closes that gap with a single idea.

**The Career Graph thesis.** Atlas builds one continuously-updated graph of a person's skills,
achievements, roles, and trajectory, owned by the candidate and legible *with consent* to
employers and universities. Every module is a **lens on this one shared graph**, never a
bolted-on feature. Talentbank's universities and employers in a single graph is a moat
incumbents cannot structurally copy — they each own only one or two sides of the table. This is
why Atlas fits the Career OS vision precisely: it is not a better job board, it is the
connective tissue between every stage of a working life.

**Primary audience: all three, in equal billing.** Atlas is one product with three coherent
control rooms over the same graph. **Navigator** gives candidates their realistic next moves,
their worth, and a coach that watches their back for decades. **Talent Radar** gives employers
people heading where the role leads, early flight-risk signals, and a workforce plan that
survives demographics. **Outcomes Studio** gives universities decades of outcome tracking,
curriculum aligned to where the market is *going*, and proof their graduates are ready. A fourth
admin **Mission Control** runs tenants, taxonomy, trust, AI cost, and audit.

**What we will build** — using both Challenge Module references and our own wildcards:

- **Career Path Navigator → Trajectory Atlas:** an interactive constellation of realistic next
  moves, each route showing a salary range, a time-to-reach band, feasibility, the skill gap,
  and trade-offs.
- **AI Career Coach → Career Copilot:** a streaming coach that reasons over your graph and
  market data, cites its sources, and shows its uncertainty.
- **Fair Pay Engine:** P25/P50/P75 market ranges for your role and region, with a negotiation
  script and the right timing.
- **Smart Talent Matching:** trajectory-aware, two-sided, fully explainable, consent-gated.
- **Retention Signals:** consented quiet signals — activity drop, peers leaving — surfaced to a
  manager while there is still time to act.
- **Lifelong Outcome Loop & Adaptive Readiness:** graduate outcomes tracked from
  first-destination onward, and a live employability signal that grows with each student.

Plus our **wildcards**: a **Glass Box** explainability layer reused across every AI surface; a
**Consent Center** for granular, time-boxed, revocable data rights; **Career Weather** for a
plain-language local-market briefing; **Skill Half-Life** for tracking how fast skills decay;
and a **Bias Auditor** that de-biases job-description language before posting.

**Three non-negotiable commitments** make Atlas trustworthy where AI career tools usually
aren't. *Glass Box, never black box:* every AI output ships with a rationale, evidence
citations, a confidence band, and "what would change this" — no naked scores. *Ranges, not
answers:* we show the realistic spread of outcomes for people of similar shape, with trade-offs;
the user always chooses. *Data dignity:* the candidate owns the graph, and PDPA/GDPR-native
consent governs every cross-party read, with full export and erasure.

**System-design coherence.** One graph, many lenses — clean domain boundaries on a FastAPI
backend (router/service/repository per domain), a React SPA with four role-scoped workspaces
sharing one component library, and PostgreSQL + pgvector as the spine. Consent is enforced at
the repository layer, audit is append-only, and matching/search run on hybrid semantic + keyword
retrieval fused with RRF.

**AI craft.** Azure OpenAI (gpt-4o-class + text-embedding-3-large) sits behind a swappable
`LLMClient` Protocol, with a deterministic mock for offline demos and CI. Every verdict is a
structured, schema-validated object carrying its Glass Box; RAG grounds answers; guardrails
delimit untrusted content, redact PII, refuse fabrication, and meter cost in a per-org ledger.

**28-day build confidence.** The work is tiered honestly. Tier A is the production-deep,
end-to-end demo spine — auth/RBAC, the Career Graph + taxonomy, résumé parsing, hybrid search,
matching, and the five signature AI features — and it is already standing. Tier B features are
functional but lighter; Tier C features are designed and scaffolded with clear extension points.
The README ships an honest maturity matrix because honesty is part of the craft.

---

## Build scope

**Career OS + Challenge Modules** (Career Path Navigator, AI Career Coach, Fair Pay Engine,
Smart Talent Matching, Retention Signals, Lifelong Outcome Loop, Adaptive Readiness, Future-State
Curriculum) **+ wildcards** (Glass Box, Consent Center, Career Weather, Skill Half-Life, Bias
Auditor). **Primary audience: candidates, employers, and universities — equal billing**, over
one Career Graph, with an admin Mission Control.

## Supporting materials

- Live demo URL (working Tier A core, doubling as the clickable prototype).
- `README.md` with architecture diagram and an honest feature maturity matrix.
- `docs/architecture/overview.md` and `docs/architecture/api-contract.md`.
- `docs/ai-provenance.md` (AI declaration) and `docs/DEMO.md` (5-minute judge script).
- Design spec: `docs/superpowers/specs/2026-06-14-atlas-career-os-design.md`.

## Team

| Field | Detail |
|---|---|
| Team name | [Team name] |
| Member 1 — name | [Full name] |
| Member 1 — role | [Role] |
| Member 1 — email | [Email] |
| Member 1 — mobile | [Mobile] |
| Member 1 — country | [Country] |
| Member 1 — university / company | [University/Company] |
| Member 2 — name | [Full name] |
| Member 2 — role | [Role] |
| Member 2 — email | [Email] |
| Member 2 — mobile | [Mobile] |
| Member 2 — country | [Country] |
| Member 2 — university / company | [University/Company] |
| Member 3 — name | [Full name] |
| Member 3 — role | [Role] |
| Member 3 — email | [Email] |
| Member 3 — mobile | [Mobile] |
| Member 3 — country | [Country] |
| Member 3 — university / company | [University/Company] |

*Add or remove member rows as needed.*
