import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft,
  Banknote,
  Briefcase,
  Check,
  MapPin,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { EmptyState, PageHeader, Spinner } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiClientError } from "@/lib/apiClient";
import { cn, formatCurrency, formatPercent } from "@/lib/utils";
import { MatchRing } from "../components/MatchBadge";
import { useApply, useJob, useJobMatch, type JobMatch } from "../api";

const SUB_LABELS: Record<keyof JobMatch["sub_scores"], string> = {
  semantic: "Semantic fit",
  skill_overlap: "Skill overlap",
  trajectory_fit: "Trajectory fit",
  salary_fit: "Salary fit",
};

export default function JobDetail() {
  const { jobId } = useParams<{ jobId: string }>();
  const job = useJob(jobId);
  const match = useJobMatch(jobId);
  const apply = useApply();
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [applied, setApplied] = useState(false);

  function submitApplication() {
    if (!jobId) return;
    apply.mutate(
      { job_id: jobId, cover_note: note.trim() || undefined },
      {
        onSuccess: () => {
          setApplied(true);
          setOpen(false);
          toast.success("Application submitted");
        },
        onError: (e) =>
          toast.error(e instanceof ApiClientError ? e.message : "Could not apply. Try again."),
      },
    );
  }

  if (job.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (job.isError || !job.data) {
    return (
      <EmptyState
        icon={Briefcase}
        title="Job not found"
        description="This role may have been closed or removed."
        action={
          <Button asChild variant="outline">
            <Link to="/app/jobs">Back to discovery</Link>
          </Button>
        }
      />
    );
  }

  const j = job.data;
  const company = j.company ?? j.org_name ?? "Confidential";
  const currency = j.currency ?? "MYR";

  return (
    <div className="animate-fade-in space-y-6">
      <Link
        to="/app/jobs"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Back to discovery
      </Link>

      <PageHeader
        eyebrow={company}
        title={j.title}
        action={
          applied ? (
            <Button variant="outline" disabled>
              <Check /> Applied
            </Button>
          ) : (
            <Button variant="brand" onClick={() => setOpen(true)}>
              Apply now
            </Button>
          )
        }
      />

      <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <MapPin className="h-4 w-4" />
          {j.location}
          {j.work_mode ? ` · ${j.work_mode}` : ""}
        </span>
        {j.seniority && (
          <span className="flex items-center gap-1.5 capitalize">
            <Briefcase className="h-4 w-4" />
            {j.seniority}
          </span>
        )}
        {j.comp_min != null && j.comp_max != null && (
          <span className="flex items-center gap-1.5">
            <Banknote className="h-4 w-4" />
            {formatCurrency(j.comp_min, currency)}–{formatCurrency(j.comp_max, currency)}
          </span>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* JD */}
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardContent className="space-y-4 p-6">
              <h2 className="font-display text-lg font-semibold">About the role</h2>
              <p className="whitespace-pre-wrap leading-relaxed text-foreground/90">
                {j.description}
              </p>
              {(j.requirements ?? []).length > 0 && (
                <div>
                  <h3 className="mb-2 font-semibold">Requirements</h3>
                  <ul className="space-y-1.5 text-sm">
                    {(j.requirements ?? []).map((r, i) => (
                      <li key={i} className="flex gap-2">
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {(j.skills_required ?? []).length > 0 && (
                <div>
                  <h3 className="mb-2 font-semibold">Skills</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {(j.skills_required ?? []).map((s) => (
                      <Badge key={s} variant="secondary">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {(j.growth_into ?? []).length > 0 && (
                <div>
                  <h3 className="mb-2 flex items-center gap-1.5 font-semibold">
                    <TrendingUp className="h-4 w-4 text-brand" /> Grows into
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    {(j.growth_into ?? []).map((s) => (
                      <Badge key={s} variant="brand">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Match */}
        <div className="space-y-4">
          <Card className="border-brand/30">
            <CardContent className="p-6">
              <h2 className="mb-4 flex items-center gap-2 font-display text-lg font-semibold">
                <Sparkles className="h-4 w-4 text-brand" /> Your match
              </h2>
              {match.isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Spinner className="h-5 w-5 text-brand" />
                </div>
              ) : match.isError || !match.data ? (
                <p className="text-sm text-muted-foreground">
                  Match explanation isn't available for this role yet.
                </p>
              ) : (
                <>
                  <div className="flex items-center gap-4">
                    <MatchRing score={match.data.score} size={72} />
                    <p className="text-sm text-muted-foreground">
                      How well this role fits your Career Graph today.
                    </p>
                  </div>
                  <div className="mt-5 space-y-3">
                    {(Object.keys(match.data.sub_scores) as (keyof JobMatch["sub_scores"])[]).map(
                      (k) => (
                        <div key={k}>
                          <div className="mb-1 flex justify-between text-xs">
                            <span className="text-muted-foreground">{SUB_LABELS[k]}</span>
                            <span className="font-medium tabular-nums">
                              {formatPercent(match.data!.sub_scores[k])}
                            </span>
                          </div>
                          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                            <div
                              className={cn(
                                "h-full rounded-full bg-gradient-to-r from-primary to-brand",
                              )}
                              style={{ width: `${match.data!.sub_scores[k] * 100}%` }}
                            />
                          </div>
                        </div>
                      ),
                    )}
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {match.data?.glass_box && (
            <GlassBoxPanel glassBox={match.data.glass_box} title="Why this match score" />
          )}
        </div>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Apply to {j.title}</DialogTitle>
            <DialogDescription>
              Add an optional note for {company}. Your Career Graph is shared with your consent.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Why you're a great fit (optional)…"
            rows={5}
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)} disabled={apply.isPending}>
              Cancel
            </Button>
            <Button variant="brand" onClick={submitApplication} disabled={apply.isPending}>
              {apply.isPending ? <Spinner /> : "Submit application"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
