# Atlas — Video Demo Script

A scene-by-scene script for recording a demo of **Atlas — Asia's Career OS**. Tuned to the
seeded data so everything you click has real content behind it. Everything runs on the
**deterministic mock LLM by default** — no API keys needed, every AI surface responds.

- **Full version:** ~6–7 min (all three audiences + the system story).
- **Short version:** ~90 s (at the end).
- **Recording tips:** at the bottom.

---

## 0 · Pre-flight (before you hit record)

**Run it** (pick one):
- Local: `docker compose up` → app at **http://localhost:5173**, API docs at http://localhost:8000/docs
- Or the live URL once deployed (see [DEPLOY.md](DEPLOY.md)).

**Login:** the sign-in screen has **one-click demo buttons** — Candidate / Employer / University /
Admin (password `demo1234` if you type them: `aisyah@demo.atlas`, `daniel@demo.atlas`,
`dr.tan@demo.atlas`, `admin@demo.atlas`).

**Set up:** dark mode on (top-right toggle), browser ≥1280×800, zoom 100%, other tabs closed. To
show the **real-time notification** moment, open two windows side by side (candidate + employer).

**Open with this line:**
> "Job boards see jobs. ATS systems see filters. Universities see graduation. **Nobody sees a
> career as one continuous thing — Atlas does.** It's one Career Graph seen through three control
> rooms. A map, not a fortune-teller: every AI answer is a Glass Box, and it shows ranges, not
> naked scores."

---

## 1 · The hook — Landing `/` (~25s)
- Scroll the hero slowly; read *"A map, not a fortune-teller."*
- **Say:** "Across Asia, careers are built alone, in the dark. Atlas shows you the landscape and
  the realistic range of outcomes for people like you — and leaves the choice to you."
- Click **Sign in**.

---

## 2 · Candidate — Aisyah (Navigator) · ~2:30
Click the **Candidate** demo button → lands on `/app`.

1. **Dashboard `/app`** — "Her career at a glance: applications, **40 trajectory-aligned matches**,
   100% profile, and a *Sunny* market outlook — Data Scientist ~RM9,500/mo, demand rising +7%."
   Point at the match list (AirAsia, Maybank, Shopee with % scores). *"Not keyword matches —
   trajectory matches."*
2. **Trajectory Atlas `/app/atlas`** ⭐ *(signature view)* — "Not one answer — a handful of
   **realistic routes** from where she is now, each with a salary range, a time-to-reach band,
   feasibility, the skill gap, and the trade-offs." Open the **Glass Box** on a route — rationale +
   citations + confidence + *what would change this*. *"Every AI judgement carries its reasoning,
   its sources, and its uncertainty. No black-box scores."*
3. **Career Copilot `/app/coach`** ⭐ *(live AI)* — ask *"Should I take a data role that grows into
   ML?"* → show the **streaming** reply (SSE) that **cites sources and states uncertainty**. Let it
   finish on camera — the streaming *is* the proof it's live.
4. **Fair Pay `/app/pay`** — "Is she paid what she's worth? **P25/P50/P75** against real Malaysian
   wage data (DOSM), the gap verdict, and a **negotiation script + timing** for before her review."
5. **CV / PDF export `/app/cv`** ⭐ *(the self-writing CV)* — "Her CV writes itself from the Career
   Graph — always current, always true." Click **Download PDF** → show the clean, chrome-free résumé.
6. **Data & Consent `/app/consent`** — "She **owns** the graph: granular, time-boxed, **revocable**
   consent, plus a who-viewed-what access log. PDPA-native. Export or erase anytime."

---

## 3 · Employer — Daniel (Talent Radar) · ~1:30
Click the **Employer** demo button → lands on `/employer`.

1. **Find talent `/employer/candidates`** ⭐ — pick a role, open a match. Show the
   **trajectory-aware score with sub-scores** (semantic, skill overlap, trajectory fit, salary fit)
   and its **Glass Box**. *"Consent-gated — he only sees candidates who granted access. No spam, no
   scraping."*
2. **Jobs → Bias Auditor `/employer/jobs`** — on a draft job, run **debias**: flagged phrases, *why*
   each is a problem, and the rewrite. *"Helps employers hire fairly."*
3. **Retention Signals `/employer/retention`** — a consented quiet signal (activity drop / peers
   leaving) with evidence and a manager talking-point. *"A nudge while there's still time."*

---

## 4 · University — Dr. Tan (Outcomes Studio) · ~1:00
Click the **University** demo button → lands on `/university`.

1. **Outcome Loop `/university/outcomes`** ⭐ — "Most platforms go blind a year after graduation.
   Atlas follows graduates onward: employment rate, median salary, by-field, trend over time — fed
   back into teaching."
2. **Readiness Profiles `/university/readiness`** — open a student's **Adaptive Readiness Profile**:
   the live employability score, its explained dimensions, and the Glass Box.
3. **Curriculum Engine `/university/curriculum`** — the market-vs-program **skill-gap** view with
   recommendations. *"Students graduate into skills that still matter."*

---

## 5 · The system story + real-time moment · ~45s
*Best with two windows: Aisyah (left) + Daniel (right).*

- **Say:** "It's **one** Career OS — three control rooms over one shared graph."
- In **Aisyah's** window: `/app/jobs` → open one of Daniel's company's roles → **Apply**.
- Cut to **Daniel's** window: the **notification bell pings in real time** (WebSocket) and a toast
  appears. Open the bell to show the new application. *"Both sides, connected honestly, in real time."*
- *Single-window fallback:* just open the bell — the unread badge and panel are already live.

---

## 6 · (Optional) Trust & governance — Admin `/admin` · ~25s
Click the **Admin** demo button.
- **AI Usage & Cost `/admin/ai-usage`** — the per-org **cost ledger** (total, by-feature, by-day,
  tokens). *"Every AI call is metered and attributable."*
- **Audit Log `/admin/audit`** — the append-only record of sensitive-data access.

---

## Close (~15s)
> "Atlas doesn't tell anyone what their career *will* be. It gives them a better view of the
> landscape than they could assemble alone — and leaves the choice to them. From a first profile at
> 16 to a final pivot at 65. That's Career OS, made real."

---

## 90-second short cut
1. Landing thesis (10s) →
2. **Trajectory Atlas** + Glass Box (25s) →
3. **Career Copilot** streaming one answer (15s) →
4. Employer **Find talent** — consent-gated, explainable match (20s) →
5. The **real-time notification** moment (15s) →
6. Close line (15s).

---

## Recording tips
- **AI:** with `USE_MOCK_LLM=true` (default) the Copilot/Atlas still stream structured, on-brand
  output — fully demoable offline. For the richest answers, set the four `AZURE_OPENAI_*` vars and
  `USE_MOCK_LLM=false` (see [../backend/.env.example](../backend/.env.example)); outputs are the
  same *shape* either way.
- **Reset the demo data:** `docker compose down -v && docker compose up` (re-seeds fresh). If a page
  looks empty in local dev, the seed step hasn't run — `python -m app.scripts.seed`.
- **Show the Glass Box at least twice** — it's the differentiator the brief asks for ("explain why,
  show uncertainty, no black-box scores").
- **Backup for "is this real?":** the API docs at `http://localhost:8000/docs` show the explainable
  Glass Box payload shape live.
- **Don't** resize the window mid-record (layout reflow). Let streaming finish on camera.
- If a **Tier-C** page looks sparse, name it: "scaffolded, on the 28-day roadmap" — don't dwell.
