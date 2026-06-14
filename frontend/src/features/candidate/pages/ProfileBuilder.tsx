import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Briefcase, Plus, Save, Sparkles, Trash2, Wand2, X } from "lucide-react";
import { PageHeader, SectionHeading, Spinner } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiClientError } from "@/lib/apiClient";
import { cn, formatPercent } from "@/lib/utils";
import {
  toPercent100,
  useParseResume,
  useProfile,
  useUpdateProfile,
  type CandidateProfile,
  type CareerEvent,
  type CandidateSkill,
} from "../api";

type Draft = Pick<
  CandidateProfile,
  "headline" | "summary" | "location" | "aspirations" | "target_occupation"
> & { career_events: CareerEvent[]; skills: CandidateSkill[] };

const EMPTY_DRAFT: Draft = {
  headline: "",
  summary: "",
  location: "",
  aspirations: "",
  target_occupation: "",
  career_events: [],
  skills: [],
};

export default function ProfileBuilder() {
  const profile = useProfile();
  const update = useUpdateProfile();
  const parse = useParseResume();

  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [resumeText, setResumeText] = useState("");
  const [newSkill, setNewSkill] = useState("");

  useEffect(() => {
    if (profile.data) {
      setDraft({
        headline: profile.data.headline ?? "",
        summary: profile.data.summary ?? "",
        location: profile.data.location ?? "",
        aspirations: profile.data.aspirations ?? "",
        target_occupation: profile.data.target_occupation ?? "",
        career_events: profile.data.career_events ?? [],
        skills: profile.data.skills ?? [],
      });
    }
  }, [profile.data]);

  const completeness = computeCompleteness(draft, profile.data?.completeness);

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  function save() {
    update.mutate(draft, {
      onSuccess: () => toast.success("Profile saved"),
      onError: (e) =>
        toast.error(e instanceof ApiClientError ? e.message : "Couldn't save profile."),
    });
  }

  function runParse() {
    if (!resumeText.trim()) return;
    parse.mutate(resumeText.trim(), {
      onError: (e) =>
        toast.error(e instanceof ApiClientError ? e.message : "Couldn't parse resume."),
    });
  }

  function applyParsed() {
    const r = parse.data;
    if (!r) return;
    setDraft((d) => ({
      ...d,
      headline: d.headline || r.headline || "",
      summary: d.summary || r.summary || "",
      career_events: [...d.career_events, ...(r.career_events ?? [])],
      skills: mergeSkills(d.skills, r.skills ?? []),
    }));
    parse.reset();
    setResumeText("");
    toast.success("Parsed details added to your profile draft");
  }

  function addSkill() {
    const name = newSkill.trim();
    if (!name) return;
    if (draft.skills.some((s) => s.skill.toLowerCase() === name.toLowerCase())) {
      setNewSkill("");
      return;
    }
    set("skills", [...draft.skills, { skill: name, proficiency: 0.5 }]);
    setNewSkill("");
  }

  if (profile.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      <PageHeader
        eyebrow="Your Career Graph"
        title="Profile builder"
        description="The richer your profile, the sharper every match, route, and forecast becomes."
        action={
          <Button variant="brand" onClick={save} disabled={update.isPending}>
            {update.isPending ? <Spinner /> : <Save />} Save profile
          </Button>
        }
      />

      {/* Completeness */}
      <Card>
        <CardContent className="flex items-center gap-4 p-5">
          <div className="flex-1">
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="font-medium">Profile completeness</span>
              <span className="font-semibold text-brand tabular-nums">{completeness}%</span>
            </div>
            <Progress value={completeness} />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Basics */}
        <Card>
          <CardContent className="space-y-4 p-6">
            <SectionHeading title="Basics" />
            <Field label="Headline">
              <Input
                value={draft.headline}
                onChange={(e) => set("headline", e.target.value)}
                placeholder="e.g. Senior Data Analyst turning insights into decisions"
              />
            </Field>
            <Field label="Location">
              <Input
                value={draft.location}
                onChange={(e) => set("location", e.target.value)}
                placeholder="e.g. Kuala Lumpur, MY"
              />
            </Field>
            <Field label="Summary">
              <Textarea
                value={draft.summary}
                onChange={(e) => set("summary", e.target.value)}
                rows={4}
                placeholder="A short professional summary…"
              />
            </Field>
            <Field label="Aspirations">
              <Textarea
                value={draft.aspirations}
                onChange={(e) => set("aspirations", e.target.value)}
                rows={2}
                placeholder="Where do you want to be in a few years?"
              />
            </Field>
            <Field label="Target occupation">
              <Input
                value={draft.target_occupation}
                onChange={(e) => set("target_occupation", e.target.value)}
                placeholder="e.g. Data Science Manager"
              />
            </Field>
          </CardContent>
        </Card>

        {/* Resume parse */}
        <Card>
          <CardContent className="space-y-4 p-6">
            <SectionHeading
              title="Import from resume"
              description="Paste your resume — Atlas extracts roles and skills with a confidence on each."
            />
            <Textarea
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              rows={6}
              placeholder="Paste your resume text here…"
            />
            <Button
              variant="outline"
              onClick={runParse}
              disabled={parse.isPending || !resumeText.trim()}
            >
              {parse.isPending ? <Spinner /> : <Wand2 />} Parse resume
            </Button>

            {parse.data && (
              <div className="space-y-3 rounded-xl border border-brand/20 bg-accent/30 p-4">
                <div className="flex items-center justify-between">
                  <p className="flex items-center gap-2 text-sm font-medium">
                    <Sparkles className="h-4 w-4 text-brand" /> Parsed preview
                  </p>
                  <Button size="sm" variant="brand" onClick={applyParsed}>
                    <Plus className="h-3.5 w-3.5" /> Add to profile
                  </Button>
                </div>

                {(parse.data.career_events ?? []).length > 0 && (
                  <div>
                    <p className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
                      Experience
                    </p>
                    <div className="space-y-1.5">
                      {parse.data.career_events.map((ev, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between rounded-lg bg-card/70 px-3 py-1.5 text-sm"
                        >
                          <span className="min-w-0 truncate">
                            {ev.title}
                            {ev.organization ? ` · ${ev.organization}` : ""}
                          </span>
                          <ConfidencePill value={ev.confidence} />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {(parse.data.skills ?? []).length > 0 && (
                  <div>
                    <p className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
                      Skills
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {parse.data.skills.map((s, i) => (
                        <Badge key={i} variant="secondary" className="gap-1">
                          {s.skill}
                          {s.confidence != null && (
                            <span className="text-[10px] opacity-70">
                              {formatPercent(s.confidence)}
                            </span>
                          )}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                <GlassBoxPanel
                  glassBox={parse.data.glass_box}
                  title="How Atlas parsed this"
                  defaultOpen={false}
                />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Career events */}
      <Card>
        <CardContent className="space-y-4 p-6">
          <div className="flex items-center justify-between">
            <SectionHeading title="Career timeline" />
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                set("career_events", [
                  ...draft.career_events,
                  { id: crypto.randomUUID(), title: "", organization: "" },
                ])
              }
            >
              <Plus className="h-4 w-4" /> Add role
            </Button>
          </div>
          {draft.career_events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No roles yet. Add one or import a resume.</p>
          ) : (
            <div className="space-y-3">
              {draft.career_events.map((ev, idx) => (
                <div key={ev.id || idx} className="rounded-xl border p-4">
                  <div className="flex items-center gap-2">
                    <Briefcase className="h-4 w-4 text-muted-foreground" />
                    <Input
                      value={ev.title}
                      placeholder="Job title"
                      onChange={(e) =>
                        set(
                          "career_events",
                          draft.career_events.map((x, i) =>
                            i === idx ? { ...x, title: e.target.value } : x,
                          ),
                        )
                      }
                    />
                    <Input
                      value={ev.organization ?? ""}
                      placeholder="Organization"
                      onChange={(e) =>
                        set(
                          "career_events",
                          draft.career_events.map((x, i) =>
                            i === idx ? { ...x, organization: e.target.value } : x,
                          ),
                        )
                      }
                    />
                    <Button
                      size="icon"
                      variant="ghost"
                      className="shrink-0 text-muted-foreground"
                      onClick={() =>
                        set(
                          "career_events",
                          draft.career_events.filter((_, i) => i !== idx),
                        )
                      }
                      aria-label="Remove role"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Skills */}
      <Card>
        <CardContent className="space-y-4 p-6">
          <SectionHeading title="Skills" description="Set proficiency for each — drag isn't needed, just edit." />
          <div className="flex gap-2">
            <Input
              value={newSkill}
              onChange={(e) => setNewSkill(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addSkill();
                }
              }}
              placeholder="Add a skill…"
              className="max-w-xs"
            />
            <Button variant="outline" onClick={addSkill}>
              <Plus className="h-4 w-4" /> Add
            </Button>
          </div>
          {draft.skills.length === 0 ? (
            <p className="text-sm text-muted-foreground">No skills yet.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {draft.skills.map((s, idx) => (
                <div key={`${s.skill}-${idx}`} className="rounded-lg border p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-sm font-medium">{s.skill}</span>
                    <button
                      type="button"
                      onClick={() =>
                        set(
                          "skills",
                          draft.skills.filter((_, i) => i !== idx),
                        )
                      }
                      className="text-muted-foreground hover:text-destructive"
                      aria-label={`Remove ${s.skill}`}
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={Math.round(s.proficiency * 100)}
                    onChange={(e) =>
                      set(
                        "skills",
                        draft.skills.map((x, i) =>
                          i === idx ? { ...x, proficiency: Number(e.target.value) / 100 } : x,
                        ),
                      )
                    }
                    className="w-full accent-brand"
                  />
                  <p className="mt-1 text-xs text-muted-foreground tabular-nums">
                    Proficiency {formatPercent(s.proficiency)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function ConfidencePill({ value }: { value?: number }) {
  if (value == null) return null;
  const tone =
    value >= 0.75
      ? "bg-success/15 text-success"
      : value >= 0.5
        ? "bg-warning/20 text-warning-foreground"
        : "bg-muted text-muted-foreground";
  return (
    <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold", tone)}>
      {formatPercent(value)}
    </span>
  );
}

function mergeSkills(existing: CandidateSkill[], incoming: CandidateSkill[]): CandidateSkill[] {
  const map = new Map(existing.map((s) => [s.skill.toLowerCase(), s]));
  for (const s of incoming) {
    if (!map.has(s.skill.toLowerCase())) {
      map.set(s.skill.toLowerCase(), { skill: s.skill, proficiency: s.proficiency ?? 0.5 });
    }
  }
  return Array.from(map.values());
}

function computeCompleteness(draft: Draft, fallback?: number): number {
  // Prefer the server-provided value when present; otherwise estimate locally.
  if (fallback != null) {
    const local = estimate(draft);
    return Math.max(toPercent100(fallback), local);
  }
  return estimate(draft);
}

function estimate(draft: Draft): number {
  const checks = [
    !!draft.headline,
    !!draft.summary,
    !!draft.location,
    !!draft.aspirations,
    !!draft.target_occupation,
    draft.career_events.length > 0,
    draft.skills.length >= 3,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}
