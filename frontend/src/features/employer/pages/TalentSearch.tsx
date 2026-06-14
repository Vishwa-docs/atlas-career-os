import { useState } from "react";
import { Search, ShieldCheck, Sparkles, UserSearch } from "lucide-react";
import { PageHeader, EmptyState, Spinner } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { formatPercent, initials } from "@/lib/utils";
import { useCandidateMatches, useEmployerJobs, asArray, type CandidateMatch } from "../api";

const SUB_SCORE_LABELS: Record<string, string> = {
  semantic: "Profile fit",
  skill_overlap: "Skill overlap",
  trajectory_fit: "Trajectory fit",
  salary_fit: "Salary fit",
};

function SubScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">{formatPercent(value)}</span>
      </div>
      <Progress value={value * 100} className="h-1.5" />
    </div>
  );
}

function MatchCard({ match }: { match: CandidateMatch }) {
  const c = match.candidate_summary;
  return (
    <Card className="overflow-hidden">
      <CardContent className="space-y-4 p-5">
        <div className="flex items-start gap-4">
          <Avatar className="h-12 w-12">
            {c.avatar_url && <AvatarImage src={c.avatar_url} alt={c.full_name} />}
            <AvatarFallback>{initials(c.full_name)}</AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="truncate font-semibold">{c.full_name}</h3>
                <p className="truncate text-sm text-muted-foreground">
                  {c.headline || c.current_role || "Candidate"}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="font-display text-2xl font-bold text-brand tabular-nums">
                  {formatPercent(match.score)}
                </p>
                <p className="text-xs text-muted-foreground">match</p>
              </div>
            </div>
            {(c.location || c.years_experience != null) && (
              <p className="mt-1 text-xs text-muted-foreground">
                {[c.location, c.years_experience != null ? `${c.years_experience} yrs exp` : null]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            )}
          </div>
        </div>

        {c.top_skills && c.top_skills.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {c.top_skills.slice(0, 8).map((s) => (
              <Badge key={s} variant="secondary">
                {s}
              </Badge>
            ))}
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          {Object.entries(match.sub_scores).map(([key, value]) => (
            <SubScoreBar key={key} label={SUB_SCORE_LABELS[key] ?? key} value={value} />
          ))}
        </div>

        <GlassBoxPanel glassBox={match.glass_box} defaultOpen={false} />

        <div className="flex items-start gap-2 rounded-lg bg-muted/60 p-3 text-xs text-muted-foreground">
          <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
          <span>
            {match.consent_note ??
              "This profile is shown under the candidate's active consent grant. Contact details unlock only with their explicit opt-in."}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

export default function TalentSearch() {
  const jobsQuery = useEmployerJobs();
  const jobs = asArray(jobsQuery.data);

  const [jobId, setJobId] = useState<string>("");
  const [draftQ, setDraftQ] = useState("");
  const [q, setQ] = useState("");

  const effectiveJobId = jobId || jobs[0]?.id || "";

  const { data, isLoading, isFetching, isError } = useCandidateMatches({
    job_id: effectiveJobId,
    q,
  });

  const matches = data ?? [];
  const hasInput = !!effectiveJobId || !!q;

  function onSearch(e: React.FormEvent) {
    e.preventDefault();
    setQ(draftQ.trim());
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Talent Radar"
        title="Find talent"
        description="Trajectory-aware, consent-gated candidate matching — with the reasoning behind every score."
      />

      <Card className="mb-6">
        <CardContent className="p-5">
          <form onSubmit={onSearch} className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_auto] sm:items-end">
            <div className="space-y-1.5">
              <Label htmlFor="job">Match against role</Label>
              <select
                id="job"
                value={effectiveJobId}
                onChange={(e) => setJobId(e.target.value)}
                className="flex h-10 w-full items-center justify-between rounded-lg border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {jobs.length === 0 && <option value="">No roles yet</option>}
                {jobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.title}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="q">Refine with a query</Label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="q"
                  value={draftQ}
                  onChange={(e) => setDraftQ(e.target.value)}
                  placeholder="e.g. fintech backend, leadership track"
                  className="pl-9"
                />
              </div>
            </div>
            <Button type="submit" variant="brand" disabled={!effectiveJobId && !draftQ.trim()}>
              <Sparkles className="h-4 w-4" /> Search
            </Button>
          </form>
        </CardContent>
      </Card>

      {!hasInput ? (
        <EmptyState
          icon={UserSearch}
          title="Pick a role to begin"
          description="Select one of your open roles (and optionally add a query) to surface explained candidate matches."
        />
      ) : isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-72 rounded-xl" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={UserSearch}
          title="Couldn't run that search"
          description="Something went wrong matching candidates. Adjust your query and try again."
        />
      ) : matches.length === 0 ? (
        <EmptyState
          icon={UserSearch}
          title="No consenting candidates yet"
          description="No candidates currently match this role within their consent grants. Try a broader query."
        />
      ) : (
        <>
          {isFetching && (
            <div className="mb-3 flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner /> Refreshing matches…
            </div>
          )}
          <div className="grid gap-4 lg:grid-cols-2">
            {matches.map((m) => (
              <MatchCard key={m.candidate_summary.id} match={m} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
