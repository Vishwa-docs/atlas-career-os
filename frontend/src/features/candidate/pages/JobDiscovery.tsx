import { useState } from "react";
import { Link } from "react-router-dom";
import { Banknote, Briefcase, MapPin, Search, Sparkles } from "lucide-react";
import { EmptyState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { formatCurrency } from "@/lib/utils";
import { MatchBadge } from "../components/MatchBadge";
import { asArray, useJobs, type JobFilters, type JobSummary } from "../api";

const ANY = "any";
const SENIORITY = ["intern", "junior", "mid", "senior", "lead", "principal"];
const WORK_MODE = ["onsite", "hybrid", "remote"];

export default function JobDiscovery() {
  const [draft, setDraft] = useState("");
  const [filters, setFilters] = useState<JobFilters>({ semantic: true, page: 1 });

  const { data, isLoading, isError } = useJobs(filters);
  const jobs = asArray<JobSummary>(data);
  const total = data && !Array.isArray(data) ? data.total : jobs.length;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setFilters((f) => ({ ...f, q: draft.trim(), page: 1 }));
  }

  function setFilter(key: keyof JobFilters, value: string) {
    setFilters((f) => ({ ...f, [key]: value === ANY ? undefined : value, page: 1 }));
  }

  return (
    <div className="animate-fade-in space-y-6">
      <PageHeader
        eyebrow="Discovery"
        title="Find your next role"
        description="Search by what you want to do — semantic matching understands intent, not just keywords."
      />

      <form onSubmit={submit} className="space-y-4 rounded-xl border bg-card p-4 shadow-sm">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="e.g. data scientist who mentors juniors"
              className="pl-9"
            />
          </div>
          <Button type="submit" variant="brand">
            Search
          </Button>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <Label className="text-xs">Location</Label>
            <Input
              value={filters.location ?? ""}
              onChange={(e) => setFilter("location", e.target.value)}
              placeholder="Any location"
              className="h-9 w-40"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Seniority</Label>
            <Select value={filters.seniority ?? ANY} onValueChange={(v) => setFilter("seniority", v)}>
              <SelectTrigger className="h-9 w-36 capitalize">
                <SelectValue placeholder="Any" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>Any</SelectItem>
                {SENIORITY.map((s) => (
                  <SelectItem key={s} value={s} className="capitalize">
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Work mode</Label>
            <Select value={filters.work_mode ?? ANY} onValueChange={(v) => setFilter("work_mode", v)}>
              <SelectTrigger className="h-9 w-36 capitalize">
                <SelectValue placeholder="Any" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>Any</SelectItem>
                {WORK_MODE.map((s) => (
                  <SelectItem key={s} value={s} className="capitalize">
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <label className="flex items-center gap-2 pb-1.5 text-sm">
            <Switch
              checked={!!filters.semantic}
              onCheckedChange={(c) => setFilters((f) => ({ ...f, semantic: c, page: 1 }))}
            />
            <span className="flex items-center gap-1 text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5 text-brand" /> Semantic search
            </span>
          </label>
        </div>
      </form>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-xl" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={Briefcase}
          title="Couldn't load jobs"
          description="Please try a different search or refresh."
        />
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={Search}
          title="No roles match your search"
          description="Try broadening your filters or turning on semantic search."
        />
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            {total} role{total === 1 ? "" : "s"} found
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function JobCard({ job }: { job: JobSummary }) {
  const company = job.company ?? job.org_name ?? "Confidential";
  const comp =
    job.comp_min != null && job.comp_max != null
      ? `${formatCurrency(job.comp_min)}–${formatCurrency(job.comp_max)}`
      : null;
  return (
    <Link to={`/app/jobs/${job.id}`} className="block">
      <Card className="h-full transition-shadow hover:shadow-md">
        <CardContent className="flex h-full flex-col gap-3 p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="truncate font-semibold">{job.title}</h3>
              <p className="truncate text-sm text-muted-foreground">{company}</p>
            </div>
            {job.match_score != null && <MatchBadge score={job.match_score} />}
          </div>

          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" />
              {job.location}
              {job.work_mode ? ` · ${job.work_mode}` : ""}
            </span>
            {comp && (
              <span className="flex items-center gap-1">
                <Banknote className="h-3.5 w-3.5" />
                {comp}
              </span>
            )}
          </div>

          {(job.skills_required ?? []).length > 0 && (
            <div className="mt-auto flex flex-wrap gap-1.5 pt-1">
              {(job.skills_required ?? []).slice(0, 4).map((s) => (
                <Badge key={s} variant="secondary">
                  {s}
                </Badge>
              ))}
              {(job.skills_required ?? []).length > 4 && (
                <Badge variant="outline">+{(job.skills_required ?? []).length - 4}</Badge>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
