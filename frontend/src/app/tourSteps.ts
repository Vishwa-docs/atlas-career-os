/** Guided-tour scripts per workspace. Each step navigates to a route and
 * spotlights the matching sidebar nav link (always present in the AppShell). */

import type { TourStep } from "@/components/guided-tour";
import type { Workspace } from "./nav";

const sel = (path: string) => `a[href="${path}"]`;

export const TOUR_STEPS: Record<Workspace, TourStep[]> = {
  candidate: [
    {
      route: "/app",
      selector: sel("/app"),
      title: "Your Navigator",
      body: "Your whole career at a glance — applications, trajectory-aligned matches, profile strength, and a plain-language read on your market.",
    },
    {
      route: "/app/atlas",
      selector: sel("/app/atlas"),
      title: "Trajectory Atlas",
      body: "The signature view. Not one prediction — a handful of realistic routes from where you are now, each with a salary range, a time horizon, and the trade-offs spelled out.",
    },
    {
      route: "/app/coach",
      selector: sel("/app/coach"),
      title: "Career Copilot",
      body: "A senior mentor on tap, grounded in your Career Graph and the live market. Every answer shows its reasoning, its sources, and how confident it is — the Glass Box.",
    },
    {
      route: "/app/pay",
      selector: sel("/app/pay"),
      title: "Fair Pay Engine",
      body: "Are you paid what you're worth? Benchmarked against real Malaysian wage data, with a negotiation script and the right moment to raise it.",
    },
    {
      route: "/app/cv",
      selector: sel("/app/cv"),
      title: "Your self-writing CV",
      body: "Your CV compiles itself from your Career Graph — always current, always true — and exports to a clean PDF in one click.",
    },
    {
      route: "/app/consent",
      selector: sel("/app/consent"),
      title: "You own your data",
      body: "Granular, time-boxed, revocable consent over who sees what. PDPA-native. Export or erase anytime. This is how both sides connect honestly.",
    },
  ],
  employer: [
    {
      route: "/employer",
      selector: sel("/employer"),
      title: "Talent Radar",
      body: "Your hiring command centre — pipeline health, recent activity, and signals across your talent, all over one shared Career Graph.",
    },
    {
      route: "/employer/candidates",
      selector: sel("/employer/candidates"),
      title: "Smart Talent Matching",
      body: "Find people by where they're heading, not just their last title — with an explainable, trajectory-aware score. Consent-gated: only candidates who opted in.",
    },
    {
      route: "/employer/retention",
      selector: sel("/employer/retention"),
      title: "Retention Signals",
      body: "The quiet signs someone is checking out — before the resignation letter. So a manager can have the conversation while there's still time.",
    },
    {
      route: "/employer/workforce",
      selector: sel("/employer/workforce"),
      title: "Workforce Resilience",
      body: "Plan 10–30 years out as Asia's working-age population shrinks — across hiring, retention, AI, and migration. Built on UN population data.",
    },
  ],
  university: [
    {
      route: "/university",
      selector: sel("/university"),
      title: "Outcomes Studio",
      body: "Your institution's view of what happens after graduation — across every cohort, on the same graph employers and students use.",
    },
    {
      route: "/university/outcomes",
      selector: sel("/university/outcomes"),
      title: "Lifelong Outcome Loop",
      body: "Most platforms go blind a year after graduation. Atlas follows graduates for decades — employment, salary, by field — and feeds it back into teaching.",
    },
    {
      route: "/university/readiness",
      selector: sel("/university/readiness"),
      title: "Adaptive Readiness",
      body: "A live employability signal per student — not a graduation date — that employers can read, with the reasoning shown.",
    },
    {
      route: "/university/curriculum",
      selector: sel("/university/curriculum"),
      title: "Future-State Curriculum",
      body: "Reads live job-market skill demand and flags the gaps in your curriculum, so students graduate into skills that still matter.",
    },
  ],
  admin: [
    {
      route: "/admin",
      selector: sel("/admin"),
      title: "Mission Control",
      body: "Platform health across all tenants — users, jobs, applications, and the Career Graph taxonomy.",
    },
    {
      route: "/admin/ai-usage",
      selector: sel("/admin/ai-usage"),
      title: "AI Cost Ledger",
      body: "Every AI call is metered and attributable — total spend, by feature, by day, by tokens. Governance baked in.",
    },
    {
      route: "/admin/audit",
      selector: sel("/admin/audit"),
      title: "Audit Trail",
      body: "An append-only record of every access to sensitive career data — the backbone of a trustworthy Career OS.",
    },
  ],
};
