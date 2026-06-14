import { Link } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { Building2, Clock, Send } from "lucide-react";
import { EmptyState, PageHeader, SectionHeading } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { asArray, useApplications, type Application, type ApplicationStatus } from "../api";

const COLUMNS: { status: ApplicationStatus; label: string; accent: string }[] = [
  { status: "applied", label: "Applied", accent: "bg-primary" },
  { status: "screening", label: "Screening", accent: "bg-brand" },
  { status: "interview", label: "Interview", accent: "bg-warning" },
  { status: "offer", label: "Offer", accent: "bg-success" },
  { status: "rejected", label: "Closed", accent: "bg-muted-foreground" },
];

const statusBadge: Record<string, "default" | "brand" | "warning" | "success" | "secondary"> = {
  applied: "default",
  screening: "brand",
  interview: "warning",
  offer: "success",
  rejected: "secondary",
  withdrawn: "secondary",
};

function safeDate(value?: string) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

export default function Applications() {
  const { data, isLoading, isError } = useApplications();
  const apps = asArray<Application>(data);

  const grouped = (status: ApplicationStatus) =>
    apps.filter((a) =>
      status === "rejected"
        ? a.status === "rejected" || a.status === "withdrawn"
        : a.status === status,
    );

  return (
    <div className="animate-fade-in space-y-6">
      <PageHeader
        eyebrow="Pipeline"
        title="Your applications"
        description="Track every role you've applied to and where it stands."
        action={
          <Button asChild variant="outline">
            <Link to="/app/jobs">
              <Send /> Find more roles
            </Link>
          </Button>
        }
      />

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState icon={Send} title="Couldn't load applications" description="Please refresh." />
      ) : apps.length === 0 ? (
        <EmptyState
          icon={Send}
          title="No applications yet"
          description="When you apply to roles, they'll appear here with a live status timeline."
          action={
            <Button asChild variant="brand">
              <Link to="/app/jobs">Browse jobs</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
          {COLUMNS.map((col) => {
            const items = grouped(col.status);
            return (
              <div key={col.status} className="space-y-3">
                <div className="flex items-center justify-between">
                  <SectionHeading title={col.label} />
                  <Badge variant="outline">{items.length}</Badge>
                </div>
                <div className="space-y-3">
                  {items.length === 0 ? (
                    <div className="rounded-xl border border-dashed py-8 text-center text-xs text-muted-foreground">
                      None
                    </div>
                  ) : (
                    items.map((app) => <AppCard key={app.id} app={app} accent={col.accent} />)
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AppCard({ app, accent }: { app: Application; accent: string }) {
  const company = app.company ?? app.org_name ?? "Confidential";
  const created = safeDate(app.created_at);
  const timeline = app.timeline ?? [];
  return (
    <Card className="overflow-hidden">
      <div className={cn("h-1 w-full", accent)} />
      <CardContent className="space-y-3 p-4">
        <Link to={`/app/jobs/${app.job_id}`} className="block">
          <p className="line-clamp-2 font-medium leading-tight hover:underline">{app.job_title}</p>
          <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
            <Building2 className="h-3 w-3" /> {company}
          </p>
        </Link>

        <Badge variant={statusBadge[app.status] ?? "default"} className="capitalize">
          {app.status}
        </Badge>

        {timeline.length > 0 ? (
          <ol className="space-y-2 border-l pl-3 pt-1">
            {timeline.slice(-3).map((ev, i) => {
              const at = safeDate(ev.at);
              return (
                <li key={i} className="relative text-xs">
                  <span className="absolute -left-[15px] top-1 h-2 w-2 rounded-full bg-brand" />
                  <p className="font-medium capitalize">{ev.status}</p>
                  {ev.note && <p className="text-muted-foreground">{ev.note}</p>}
                  {at && (
                    <p className="text-muted-foreground">
                      {formatDistanceToNow(at, { addSuffix: true })}
                    </p>
                  )}
                </li>
              );
            })}
          </ol>
        ) : (
          created && (
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" /> Applied {formatDistanceToNow(created, { addSuffix: true })}
            </p>
          )
        )}
      </CardContent>
    </Card>
  );
}
