/**
 * Self-writing CV — the "Living Portfolio" promise made concrete.
 *
 * Compiles the candidate's Career Graph (profile + career events + verified
 * skills) into a clean, recruiter-ready résumé and exports it to PDF via the
 * browser print pipeline (zero extra dependencies; "Save as PDF"). Because it's
 * generated from the graph, it's always current and always true.
 */

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, MapPin, Sparkles } from "lucide-react";
import { EmptyState, PageHeader, Spinner } from "@/components/common";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/apiClient";
import { formatPercent } from "@/lib/utils";
import { useAuth } from "@/stores/auth";

interface CareerEvent {
  id: string;
  type: string;
  title: string;
  organization: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  narrative: string | null;
  highlights: string[];
  skills_used: string[];
  break_reason: string | null;
}
interface CandidateSkill {
  id: string;
  name: string;
  proficiency: number;
  evidence_type: string;
}
interface CandidateMe {
  profile: {
    headline: string | null;
    summary: string | null;
    location: string | null;
    country: string | null;
    aspirations: string | null;
    years_experience: number | null;
    links: Record<string, string> | null;
  } | null;
  career_events: CareerEvent[];
  skills: CandidateSkill[];
}

const fmt = (d: string | null) =>
  d ? new Date(d).toLocaleDateString("en-MY", { month: "short", year: "numeric" }) : "";

const isEducation = (t: string) => /edu|degree|study|course|certif/i.test(t);
const isBreak = (t: string) => /break|chapter|sabbatical/i.test(t);

export default function CvBuilder() {
  const user = useAuth((s) => s.user);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["candidate", "me", "cv"],
    queryFn: () => api.get<CandidateMe>("/candidates/me"),
  });

  const { experience, education, breaks } = useMemo(() => {
    const events = data?.career_events ?? [];
    return {
      experience: events.filter((e) => !isEducation(e.type) && !isBreak(e.type)),
      education: events.filter((e) => isEducation(e.type)),
      breaks: events.filter((e) => isBreak(e.type)),
    };
  }, [data]);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner className="h-6 w-6 text-brand" />
      </div>
    );
  }
  if (isError || !data) {
    return (
      <EmptyState
        icon={Sparkles}
        title="We couldn't compile your CV"
        description="Add a few career events and skills to your profile, then try again."
      />
    );
  }

  const p = data.profile;
  const topSkills = [...(data.skills ?? [])]
    .sort((a, b) => (b.proficiency ?? 0) - (a.proficiency ?? 0))
    .slice(0, 18);

  return (
    <div className="animate-fade-in space-y-6">
      <div className="no-print">
        <PageHeader
          eyebrow="Living Portfolio"
          title="Your self-writing CV"
          description="Compiled from your Career Graph — always current, always true. Export to PDF anytime."
          action={
            <Button variant="brand" onClick={() => window.print()}>
              <Download /> Download PDF
            </Button>
          }
        />
      </div>

      {/* Print/preview surface */}
      <div
        data-cv-print
        className="mx-auto max-w-3xl rounded-xl border bg-white p-10 text-slate-900 shadow-sm"
      >
        <header className="border-b border-slate-200 pb-4">
          <h1 className="text-3xl font-bold tracking-tight">{user?.full_name ?? "Your name"}</h1>
          {p?.headline && <p className="mt-1 text-lg text-slate-600">{p.headline}</p>}
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
            {user?.email && <span>{user.email}</span>}
            {(p?.location || p?.country) && (
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" />
                {[p?.location, p?.country].filter(Boolean).join(", ")}
              </span>
            )}
            {p?.years_experience != null && <span>{p.years_experience} yrs experience</span>}
            {p?.links &&
              Object.entries(p.links).map(([k, v]) => (
                <span key={k} className="capitalize">
                  {k}: {v}
                </span>
              ))}
          </div>
        </header>

        {p?.summary && (
          <Section title="Summary">
            <p className="text-sm leading-relaxed text-slate-700">{p.summary}</p>
          </Section>
        )}

        {experience.length > 0 && (
          <Section title="Experience">
            {experience.map((e) => (
              <EventBlock key={e.id} e={e} />
            ))}
          </Section>
        )}

        {education.length > 0 && (
          <Section title="Education">
            {education.map((e) => (
              <EventBlock key={e.id} e={e} />
            ))}
          </Section>
        )}

        {topSkills.length > 0 && (
          <Section title="Skills">
            <div className="flex flex-wrap gap-2">
              {topSkills.map((s) => (
                <span
                  key={s.id}
                  className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
                >
                  {s.name}
                  {s.proficiency ? ` · ${formatPercent(s.proficiency)}` : ""}
                </span>
              ))}
            </div>
          </Section>
        )}

        {breaks.length > 0 && (
          <Section title="Career chapters">
            {breaks.map((e) => (
              <p key={e.id} className="text-sm text-slate-700">
                <span className="font-medium">{e.title}</span>
                {e.break_reason ? ` — ${e.break_reason}` : ""} ({fmt(e.start_date)} – {fmt(e.end_date) || "present"})
              </p>
            ))}
          </Section>
        )}

        <p className="mt-8 border-t border-slate-200 pt-3 text-[0.65rem] text-slate-400">
          Compiled by Atlas — Asia's Career OS · evidence-backed from the candidate's Career Graph
        </p>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="mb-2 text-xs font-bold uppercase tracking-widest text-slate-400">{title}</h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function EventBlock({ e }: { e: CareerEvent }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-4">
        <p className="font-semibold text-slate-900">
          {e.title}
          {e.organization ? <span className="font-normal text-slate-600"> · {e.organization}</span> : ""}
        </p>
        <p className="shrink-0 text-xs text-slate-500">
          {fmt(e.start_date)} – {e.is_current ? "present" : fmt(e.end_date)}
        </p>
      </div>
      {e.narrative && <p className="mt-1 text-sm text-slate-700">{e.narrative}</p>}
      {e.highlights?.length > 0 && (
        <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-700">
          {e.highlights.map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ul>
      )}
      {e.skills_used?.length > 0 && (
        <p className="mt-1 text-xs text-slate-500">{e.skills_used.join(" · ")}</p>
      )}
    </div>
  );
}
