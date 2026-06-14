# Atlas — 5-Minute Judge Demo Script

A tight click-through that hits Atlas's signature features across all four personas. Everything
runs on the **deterministic mock LLM by default**, so no keys are needed and every AI surface
responds.

**Before you start (15s).** Open the frontend (`http://localhost:5173`, or the live demo URL).
On the login screen, note the four **one-click demo buttons** — Candidate, Employer, University,
Admin. Password for all four is `demo1234`. The one-liner to open with:

> *"Atlas is one Career Graph seen through three control rooms. A map, not a fortune-teller —
> every AI answer is a Glass Box, and it shows ranges, not naked scores."*

---

## 1 · Candidate — Aisyah (Navigator) · ~2:00

**Log in:** click **Candidate** (`aisyah@demo.atlas`) → lands on `/app` (the Navigator dashboard).

1. **Dashboard** — point out the personalized stats, recent matches, and quiet nudges. *"This is
   her slice of the one Career Graph."*
2. **Trajectory Atlas** (sidebar → *Trajectory Atlas*, `/app/atlas`) — the signature view. Click a
   route in the constellation and show the **salary range, time-to-reach band, feasibility,
   skill gap, and trade-offs**. Emphasize: *ranges, not a single prediction.* Open the **Glass
   Box** on a route — rationale + citations + confidence + "what would change this."
3. **Career Copilot** (`/app/coach`) — ask: *"Should I take a data role that grows into ML?"*
   Show the **streaming** reply (SSE) and that it **cites sources and states uncertainty**.
4. **Fair Pay** (`/app/pay`) — show the **P25/P50/P75** market range for her target role, the
   gap-vs-market verdict, and the **negotiation script + timing**.
5. *(If time)* **Career Weather** (`/app/weather`) — the plain-language local-market briefing:
   sunny/cloudy/stormy outlook, rising vs cooling skills, salary drift.
6. **Data & Consent** (`/app/consent`) — show granular, **revocable** grants and the
   **who-viewed-what access log**. *"The candidate owns the graph — data dignity is built in."*

---

## 2 · Employer — Daniel (Talent Radar) · ~1:15

**Log out → log in:** click **Employer** (`daniel@demo.atlas`) → lands on `/employer`.

1. **Find talent** (`/employer/candidates`) — run a search and open a candidate match. Show the
   **trajectory-aware score with sub-scores** (semantic, skill overlap, trajectory fit, salary
   fit) and its **Glass Box**. *"These results are consent-gated — he only sees candidates who
   granted access."*
2. **Jobs → Bias Auditor** (`/employer/jobs`) — on a draft job, run **debias**: show flagged
   phrases, *why* each is a problem, and the suggested rewrite.
3. **Retention Signals** (`/employer/retention`) — show a consented quiet signal (activity drop /
   peers leaving) with evidence and a manager talking-point — *"a nudge while there's still
   time."* (Tier B.)

---

## 3 · University — Dr. Tan (Outcomes Studio) · ~1:00

**Log out → log in:** click **University** (`dr.tan@demo.atlas`) → lands on `/university`.

1. **Outcome Loop** (`/university/outcomes`) — the **Lifelong Outcome Loop**: employment rate,
   median salary, time-to-employ, by-field breakdown, trend over time. *"Most platforms go blind
   after one year — this follows graduates onward."*
2. **Readiness Profiles** (`/university/readiness`) — open a student's **Adaptive Readiness
   Profile**: the live employability score, its explained dimensions, and the Glass Box.
3. *(If time)* **Curriculum Engine** (`/university/curriculum`) — the market-vs-program **skill-gap**
   view for faculty. (Tier B.)

---

## 4 · Admin — Mission Control · ~0:30

**Log out → log in:** click **Admin** (`admin@demo.atlas`) → lands on `/admin`.

1. **AI Usage & Cost** (`/admin/ai-usage`) — the per-org **cost ledger**: total spend, by-feature,
   by-day, tokens. *"Every AI call is metered and attributable."*
2. **Audit Log** (`/admin/audit`) — the append-only record of sensitive-data access.

---

## Closing line (10s)

> *"One Career Graph, three control rooms, every answer a Glass Box with ranges instead of false
> precision — and an honest maturity matrix in the README. That's Atlas: Asia's Career OS."*

---

### Notes for the operator
- If the demo data looks empty, the **seed step hasn't run** — run `python -m app.scripts.seed`
  (local dev) before demoing.
- The **API docs** at `http://localhost:8000/docs` are a good backup to show the explainable
  Glass Box payload shape live, if a judge asks "is this real?".
- All AI runs on the mock unless `USE_MOCK_LLM=false` plus Azure keys are set — outputs are the
  same *shape* either way.
