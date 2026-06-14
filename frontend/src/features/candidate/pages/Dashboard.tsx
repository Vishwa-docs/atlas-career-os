import { Link } from "react-router-dom";
import {
  ArrowRight,
  Briefcase,
  Cloud,
  CloudRain,
  Compass,
  Lightbulb,
  Sparkles,
  Sun,
  TrendingUp,
} from "lucide-react";
import { EmptyState, PageHeader, SectionHeading, StatCard } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPercent } from "@/lib/utils";
import { useAuth } from "@/stores/auth";
import { MatchBadge } from "../components/MatchBadge";
import { useDashboard, type CoachNudge, type MarketSnapshot } from "../api";

const outlookMeta = {
  sunny: { icon: Sun, label: "Sunny", tone: "text-warning-foreground" },
  cloudy: { icon: Cloud, label: "Cloudy", tone: "text-muted-foreground" },
  stormy: { icon: CloudRain, label: "Stormy", tone: "text-destructive" },
} as const;

const nudgeTone: Record<string, string> = {
  info: "border-primary/20 bg-accent/40",
  success: "border-success/30 bg-success/5",
  warning: "border-warning/40 bg-warning/10",
};

export default function CandidateDashboard() {
  const user = useAuth((s) => s.user);
  const { data, isLoading, isError } = useDashboard();
  const firstName = user?.full_name?.split(" ")[0] ?? "there";

  return (
    <div className="animate-fade-in space-y-8">
      <PageHeader
        eyebrow="Navigator"
        title={`Welcome back, ${firstName}`}
        description="Your career, mapped. Here's where you stand and where you could go next."
        action={
          <Button asChild variant="brand">
            <Link to="/app/atlas">
              <Compass /> Open Trajectory Atlas
            </Link>
          </Button>
        }
      />

      {/* Stats */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={Sparkles}
          title="We couldn't load your dashboard"
          description="Please refresh in a moment — your Career Graph is still warming up."
        />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {(data?.stats ?? []).map((s) => (
              <StatCard
                key={s.label}
                label={s.label}
                value={s.value}
                hint={s.hint}
                tone={s.tone}
                icon={TrendingUp}
              />
            ))}
            {(data?.stats ?? []).length === 0 && (
              <Card className="sm:col-span-2 lg:col-span-4">
                <CardContent className="p-6 text-sm text-muted-foreground">
                  Complete your profile to unlock personalised stats.
                </CardContent>
              </Card>
            )}
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            {/* Recent matches */}
            <div className="lg:col-span-2">
              <SectionHeading
                title="Fresh matches for you"
                description="Roles aligned to your trajectory, not just your last title."
              />
              <div className="space-y-3">
                {(data?.recent_matches ?? []).map((m) => (
                  <Link
                    key={m.job_id}
                    to={`/app/jobs/${m.job_id}`}
                    className="group flex items-center justify-between rounded-xl border bg-card p-4 shadow-sm transition-shadow hover:shadow-md"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">{m.title}</p>
                      <p className="truncate text-sm text-muted-foreground">
                        {m.company}
                        {m.location ? ` · ${m.location}` : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 pl-3">
                      <MatchBadge score={m.score} />
                      <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                    </div>
                  </Link>
                ))}
                {(data?.recent_matches ?? []).length === 0 && (
                  <EmptyState
                    icon={Briefcase}
                    title="No matches yet"
                    description="Add a few skills and your aspirations to see roles tailored to you."
                    action={
                      <Button asChild size="sm" variant="outline">
                        <Link to="/app/jobs">Browse jobs</Link>
                      </Button>
                    }
                  />
                )}
              </div>
            </div>

            {/* Side column: nudges + weather */}
            <div className="space-y-6">
              <div>
                <SectionHeading title="Coach nudges" />
                <div className="space-y-3">
                  {(data?.nudges ?? []).map((n) => (
                    <NudgeCard key={n.id} nudge={n} />
                  ))}
                  {(data?.nudges ?? []).length === 0 && (
                    <Card>
                      <CardContent className="flex items-center gap-3 p-4 text-sm text-muted-foreground">
                        <Lightbulb className="h-4 w-4 text-brand" /> You're all caught up.
                      </CardContent>
                    </Card>
                  )}
                </div>
              </div>

              <MarketSnapshotCard snapshot={data?.market_snapshot ?? null} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function NudgeCard({ nudge }: { nudge: CoachNudge }) {
  return (
    <div className={`rounded-xl border p-4 ${nudgeTone[nudge.tone ?? "info"]}`}>
      <p className="flex items-center gap-2 text-sm font-medium">
        <Lightbulb className="h-4 w-4 text-brand" />
        {nudge.title}
      </p>
      <p className="mt-1 text-sm text-muted-foreground">{nudge.body}</p>
      {nudge.cta_label && nudge.cta_to && (
        <Button asChild size="sm" variant="ghost" className="mt-2 -ml-2 h-7 text-brand">
          <Link to={nudge.cta_to}>
            {nudge.cta_label} <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Button>
      )}
    </div>
  );
}

function MarketSnapshotCard({ snapshot }: { snapshot: MarketSnapshot | null }) {
  const meta = snapshot?.outlook ? outlookMeta[snapshot.outlook] : outlookMeta.cloudy;
  const Icon = meta.icon;
  return (
    <Card className="overflow-hidden">
      <div className="bg-gradient-to-br from-primary/10 via-brand/5 to-transparent p-5">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-muted-foreground">Market snapshot</p>
          <Icon className={`h-5 w-5 ${meta.tone}`} />
        </div>
        {snapshot ? (
          <>
            <p className="mt-2 font-display text-xl font-bold">{meta.label} outlook</p>
            {snapshot.summary && (
              <p className="mt-1 text-sm text-muted-foreground">{snapshot.summary}</p>
            )}
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              {snapshot.demand_index != null && (
                <div className="rounded-lg bg-card/70 p-2.5">
                  <p className="text-xs text-muted-foreground">Demand index</p>
                  <p className="font-semibold tabular-nums">{snapshot.demand_index}</p>
                </div>
              )}
              {snapshot.salary_drift_pct != null && (
                <div className="rounded-lg bg-card/70 p-2.5">
                  <p className="text-xs text-muted-foreground">Salary drift</p>
                  <p className="font-semibold tabular-nums text-success">
                    {snapshot.salary_drift_pct > 0 ? "+" : ""}
                    {formatPercent(snapshot.salary_drift_pct / 100, 1)}
                  </p>
                </div>
              )}
            </div>
            <Button asChild size="sm" variant="outline" className="mt-4 w-full">
              <Link to="/app/weather">See full Career Weather</Link>
            </Button>
          </>
        ) : (
          <p className="mt-2 text-sm text-muted-foreground">
            Set a target occupation to see your market outlook.
          </p>
        )}
      </div>
    </Card>
  );
}
