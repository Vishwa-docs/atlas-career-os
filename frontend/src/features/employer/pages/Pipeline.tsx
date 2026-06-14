import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { KanbanSquare, GripVertical } from "lucide-react";
import { PageHeader, EmptyState, Spinner } from "@/components/common";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatPercent, initials } from "@/lib/utils";
import {
  useEmployerJobs,
  useJobApplications,
  useMoveApplication,
  asArray,
  type PipelineApplication,
  type PipelineStatus,
} from "../api";

const COLUMNS: { status: PipelineStatus; label: string; accent: string }[] = [
  { status: "applied", label: "Applied", accent: "border-t-muted-foreground" },
  { status: "screening", label: "Screening", accent: "border-t-brand" },
  { status: "interview", label: "Interview", accent: "border-t-primary" },
  { status: "offer", label: "Offer", accent: "border-t-success" },
  { status: "rejected", label: "Rejected", accent: "border-t-destructive" },
];

function ApplicationCard({
  app,
  onDragStart,
}: {
  app: PipelineApplication;
  onDragStart: (id: string) => void;
}) {
  return (
    <div
      draggable
      onDragStart={() => onDragStart(app.id)}
      className="group cursor-grab rounded-lg border bg-card p-3 shadow-sm transition-shadow hover:shadow-md active:cursor-grabbing"
    >
      <div className="flex items-start gap-2">
        <GripVertical className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
        <Avatar className="h-8 w-8">
          {app.avatar_url && <AvatarImage src={app.avatar_url} alt={app.candidate_name} />}
          <AvatarFallback className="text-xs">{initials(app.candidate_name)}</AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{app.candidate_name}</p>
          {app.headline && (
            <p className="truncate text-xs text-muted-foreground">{app.headline}</p>
          )}
        </div>
      </div>
      {app.match_score != null && (
        <div className="mt-2 flex justify-end">
          <Badge variant="brand">{formatPercent(app.match_score)} match</Badge>
        </div>
      )}
    </div>
  );
}

export default function Pipeline() {
  const jobsQuery = useEmployerJobs();
  const jobs = asArray(jobsQuery.data);

  const [jobId, setJobId] = useState("");
  const effectiveJobId = jobId || jobs[0]?.id || "";

  const { data, isLoading, isError } = useJobApplications(effectiveJobId);
  const move = useMoveApplication(effectiveJobId);

  // Local optimistic copy so cards move instantly on drop.
  const serverApps = useMemo(() => asArray(data), [data]);
  const [apps, setApps] = useState<PipelineApplication[]>([]);
  const [dragId, setDragId] = useState<string | null>(null);

  useEffect(() => {
    setApps(serverApps);
  }, [serverApps]);

  function onDrop(status: PipelineStatus) {
    if (!dragId) return;
    const current = apps.find((a) => a.id === dragId);
    setDragId(null);
    if (!current || current.status === status) return;

    setApps((prev) => prev.map((a) => (a.id === dragId ? { ...a, status } : a)));
    move.mutate(
      { id: dragId, status },
      {
        onSuccess: () => toast.success(`Moved ${current.candidate_name} to ${status}`),
        onError: () => {
          toast.error("Couldn't update stage — reverting.");
          setApps((prev) =>
            prev.map((a) => (a.id === current.id ? { ...a, status: current.status } : a)),
          );
        },
      },
    );
  }

  const byStage = (status: PipelineStatus) => apps.filter((a) => a.status === status);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Talent Radar"
        title="Pipeline"
        description="Drag candidates across stages — moves sync instantly and notify the candidate's timeline."
        action={
          jobs.length > 0 ? (
            <div className="flex items-center gap-2">
              <Label htmlFor="pipeline-job" className="text-xs text-muted-foreground">
                Role
              </Label>
              <select
                id="pipeline-job"
                value={effectiveJobId}
                onChange={(e) => setJobId(e.target.value)}
                className="flex h-10 items-center rounded-lg border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {jobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.title}
                  </option>
                ))}
              </select>
            </div>
          ) : undefined
        }
      />

      {jobsQuery.isLoading ? (
        <Skeleton className="h-96 rounded-xl" />
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={KanbanSquare}
          title="No roles to triage"
          description="Post a role first — applications will appear here as a kanban board."
        />
      ) : isLoading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {COLUMNS.map((c) => (
            <Skeleton key={c.status} className="h-80 rounded-xl" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={KanbanSquare}
          title="Couldn't load applications"
          description="We hit a snag fetching this role's pipeline. Please try again."
        />
      ) : (
        <>
          {move.isPending && (
            <div className="mb-3 flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner /> Saving…
            </div>
          )}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
            {COLUMNS.map((col) => {
              const cards = byStage(col.status);
              return (
                <div
                  key={col.status}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => onDrop(col.status)}
                  className={cn(
                    "flex flex-col rounded-xl border border-t-2 bg-muted/30 p-3",
                    col.accent,
                  )}
                >
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-sm font-semibold">{col.label}</span>
                    <span className="rounded-full bg-card px-2 py-0.5 text-xs text-muted-foreground">
                      {cards.length}
                    </span>
                  </div>
                  <div className="flex min-h-24 flex-1 flex-col gap-2">
                    {cards.length === 0 ? (
                      <p className="rounded-lg border border-dashed py-6 text-center text-xs text-muted-foreground">
                        Drop here
                      </p>
                    ) : (
                      cards.map((app) => (
                        <ApplicationCard key={app.id} app={app} onDragStart={setDragId} />
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
