import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Banknote,
  Building2,
  CloudSun,
  Compass,
  Eye,
  GraduationCap,
  Map,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import { AtlasWordmark } from "@/components/logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const phases = [
  { age: "16–22", title: "Discover", note: "Streams, skills, first portfolio" },
  { age: "23–34", title: "Launch", note: "Right first job, know your worth" },
  { age: "35–44", title: "Compound", note: "Next moves, close gaps early" },
  { age: "45–54", title: "Pivot", note: "Lead, advise, change industry" },
  { age: "55+", title: "Pass on", note: "Boards, mentoring, wind-down" },
];

const rooms = [
  {
    icon: UserRound,
    name: "Navigator",
    who: "Candidates",
    points: ["Trajectory Atlas", "Career Copilot", "Fair Pay Engine", "Living Portfolio"],
  },
  {
    icon: Building2,
    name: "Talent Radar",
    who: "Employers",
    points: ["Trajectory-aware matching", "Retention signals", "Warm re-engagement", "Workforce planning"],
  },
  {
    icon: GraduationCap,
    name: "Outcomes Studio",
    who: "Universities",
    points: ["Decades of outcomes", "Curriculum vs. market", "Live readiness profiles", "Verified credentials"],
  },
];

const signatures = [
  { icon: Map, title: "Trajectory Atlas", body: "A constellation of realistic next moves — each with salary range, time-to-reach, and trade-offs. A map, never a single answer." },
  { icon: Sparkles, title: "Career Copilot", body: "A senior mentor's instincts, on call for decades. Quiet most of the time; speaks up when something matters." },
  { icon: Banknote, title: "Fair Pay Engine", body: "Your market range from real Malaysian wage data — plus when and how to raise it, before your next review." },
  { icon: CloudSun, title: "Career Weather", body: "A plain-language briefing on the market around your role: demand, emerging skills, salary drift." },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <header className="sticky top-0 z-40 border-b bg-background/70 backdrop-blur-xl">
        <div className="container flex h-16 items-center justify-between">
          <AtlasWordmark />
          <nav className="hidden items-center gap-8 text-sm font-medium text-muted-foreground md:flex">
            <a href="#thesis" className="hover:text-foreground">Why Atlas</a>
            <a href="#rooms" className="hover:text-foreground">Three rooms</a>
            <a href="#trust" className="hover:text-foreground">Trust</a>
            <a href="/deck.html" target="_blank" rel="noreferrer" className="hover:text-foreground">Pitch deck ↗</a>
          </nav>
          <div className="flex items-center gap-2">
            <Button variant="ghost" asChild>
              <Link to="/login">Sign in</Link>
            </Button>
            <Button variant="brand" asChild>
              <Link to="/register">
                Get started <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_50%_0%,hsl(var(--brand)/0.18),transparent)]" />
        <div className="container relative py-24 text-center sm:py-32">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <Badge variant="brand" className="mb-6 gap-1.5">
              <Compass className="h-3.5 w-3.5" /> Asia's Career OS · for candidates, employers & universities
            </Badge>
            <h1 className="mx-auto max-w-4xl font-display text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-6xl">
              For most of us, <span className="aurora-text">no one tells us what's next.</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
              Atlas is a navigation tool for a 40-year career — not a fortune-teller. It shows the
              realistic range of moves for people of your shape, explains the trade-offs, and keeps
              you findable at the right moment. You always choose.
            </p>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Button variant="brand" size="lg" asChild>
                <Link to="/register">
                  Start navigating <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link to="/login">Explore the demo</Link>
              </Button>
              <Button variant="ghost" size="lg" asChild>
                <a href="/deck.html" target="_blank" rel="noreferrer">
                  View the pitch deck <ArrowRight className="h-4 w-4" />
                </a>
              </Button>
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              Try seeded demo accounts — candidate, employer, university & admin.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Career arc */}
      <section className="border-y bg-card/40 py-14">
        <div className="container">
          <p className="mb-8 text-center text-sm font-semibold uppercase tracking-widest text-brand">
            A career is continuous, not transactional
          </p>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            {phases.map((p, i) => (
              <motion.div
                key={p.title}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className="rounded-xl border bg-card p-4 text-center"
              >
                <div className="text-xs font-medium text-muted-foreground">{p.age}</div>
                <div className="mt-1 font-display text-lg font-bold">{p.title}</div>
                <div className="mt-1 text-xs text-muted-foreground">{p.note}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Thesis */}
      <section id="thesis" className="container py-20">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
            One <span className="aurora-text">Career Graph</span>. Three control rooms.
          </h2>
          <p className="mt-4 text-muted-foreground">
            Every other tool is episodic — job boards see jobs, universities see graduation, ATS sees
            filters. Atlas keeps one portable, candidate-owned graph of your skills, achievements and
            trajectory that compounds for decades, and is legible — with your consent — to the people
            who can help.
          </p>
        </div>
      </section>

      {/* Three rooms */}
      <section id="rooms" className="container pb-20">
        <div className="grid gap-6 lg:grid-cols-3">
          {rooms.map((room, i) => (
            <motion.div
              key={room.name}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              <Card className="h-full">
                <CardContent className="p-6">
                  <div className="mb-4 inline-flex rounded-xl bg-gradient-to-br from-primary/15 to-brand/15 p-3">
                    <room.icon className="h-6 w-6 text-brand" />
                  </div>
                  <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {room.who}
                  </div>
                  <h3 className="font-display text-xl font-bold">{room.name}</h3>
                  <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                    {room.points.map((pt) => (
                      <li key={pt} className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-brand" /> {pt}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Signatures */}
      <section className="border-y bg-card/40 py-20">
        <div className="container">
          <h2 className="mb-12 text-center font-display text-3xl font-bold tracking-tight">
            Signature intelligence
          </h2>
          <div className="grid gap-6 sm:grid-cols-2">
            {signatures.map((s) => (
              <div key={s.title} className="flex gap-4 rounded-xl border bg-card p-6">
                <div className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <s.icon className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-semibold">{s.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{s.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust */}
      <section id="trust" className="container py-20">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div>
            <Badge variant="success" className="mb-4 gap-1.5">
              <Eye className="h-3.5 w-3.5" /> Glass Box, never black box
            </Badge>
            <h2 className="font-display text-3xl font-bold tracking-tight">
              We explain every recommendation — and where the uncertainty sits.
            </h2>
            <p className="mt-4 text-muted-foreground">
              No naked scores. No false precision. Every AI judgement in Atlas carries a plain-language
              rationale, the evidence it used, a confidence band, and what would change its mind.
            </p>
          </div>
          <Card>
            <CardContent className="space-y-4 p-6">
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-5 w-5 text-success" />
                <div>
                  <div className="font-medium">You own your graph</div>
                  <div className="text-sm text-muted-foreground">
                    Granular, time-boxed, revocable consent. PDPA & GDPR-native. Export or erase anytime.
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Sparkles className="h-5 w-5 text-brand" />
                <div>
                  <div className="font-medium">Ranges, not answers</div>
                  <div className="text-sm text-muted-foreground">
                    The realistic spread for people like you — with the trade-offs spelled out.
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-10">
        <div className="container flex flex-col items-center justify-between gap-4 text-sm text-muted-foreground sm:flex-row">
          <AtlasWordmark />
          <p>Built for the Talentbank Tech Hackathon · First Cohort 2026</p>
          <div className="flex gap-4">
            <Link to="/login" className="hover:text-foreground">Sign in</Link>
            <Link to="/register" className="hover:text-foreground">Get started</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
