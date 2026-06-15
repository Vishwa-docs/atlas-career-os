import {
  Activity,
  Briefcase,
  Clock,
  TrendingDown,
  Users,
} from "lucide-react";
import {
  FunnelChart,
  Funnel,
  LabelList,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from "recharts";
import { PageHeader, SectionHeading, StatCard, EmptyState, Spinner } from "@/components/common";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useEmployerDashboard, type PipelineStage } from "../api";

const FUNNEL_COLORS = [
  "hsl(var(--brand))",
  "hsl(var(--primary))",
  "hsl(var(--success))",
  "hsl(var(--warning))",
  "hsl(var(--muted-foreground))",
];

function FunnelCard({ pipeline }: { pipeline: PipelineStage[] }) {
  const data = pipeline.map((s, i) => ({
    name: s.stage,
    value: s.count,
    fill: FUNNEL_COLORS[i % FUNNEL_COLORS.length],
  }));

  return (
    <Card>
      <CardContent className="p-5">
        <SectionHeading title="Hiring funnel" description="Candidates by stage, across all open roles" />
        {data.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No pipeline yet"
            description="As candidates apply, your funnel will populate here."
          />
        ) : (
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <FunnelChart>
                <RechartsTooltip
                  contentStyle={{
                    background: "hsl(var(--popover))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Funnel dataKey="value" data={data} isAnimationActive>
                  <LabelList
                    position="right"
                    fill="hsl(var(--foreground))"
                    stroke="none"
                    dataKey="name"
                    fontSize={12}
                  />
                  <LabelList
                    position="center"
                    fill="hsl(var(--primary-foreground))"
                    stroke="none"
                    dataKey="value"
                    fontSize={13}
                  />
                  {data.map((d, i) => (
                    <Cell key={i} fill={d.fill} />
                  ))}
                </Funnel>
              </FunnelChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { data, isLoading, isError } = useEmployerDashboard();

  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Talent Radar" title="Employer dashboard" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <div className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> Loading your radar…
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Talent Radar" title="Employer dashboard" />
        <EmptyState
          icon={Activity}
          title="Couldn't load your dashboard"
          description="We hit a snag fetching your hiring metrics. Please try again shortly."
        />
      </div>
    );
  }

  const activity = data.recent_activity ?? [];
  const ttf = data.time_to_fill;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Talent Radar"
        title="Employer dashboard"
        description="Your live hiring pulse — pipeline health, time-to-fill and retention risk in one view."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Open roles" value={data.open_roles} icon={Briefcase} tone="brand" />
        <StatCard
          label="In pipeline"
          value={data.applications_total ?? data.pipeline.reduce((a, s) => a + s.count, 0)}
          icon={Users}
        />
        <StatCard
          label="Avg. time to fill"
          value={ttf == null ? "—" : `${ttf}d`}
          hint={ttf == null ? "Not enough data yet" : "Across closed roles"}
          icon={Clock}
        />
        <StatCard
          label="Flight risk"
          value={data.flight_risk_count}
          hint="Employees showing retention signals"
          icon={TrendingDown}
          tone={data.flight_risk_count > 0 ? "warning" : "success"}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <FunnelCard pipeline={data.pipeline} />
        </div>

        <div className="lg:col-span-2">
          <Card className="h-full">
            <CardContent className="p-5">
              <SectionHeading title="Recent activity" description="Latest moves across your pipeline" />
              {activity.length === 0 ? (
                <EmptyState
                  icon={Activity}
                  title="Nothing yet"
                  description="Applications, stage changes and signals will show up here."
                />
              ) : (
                <ul className="space-y-3">
                  {activity.map((a) => (
                    <li key={a.id} className="flex gap-3">
                      <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-brand" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium leading-snug">{a.title}</p>
                        {a.detail && (
                          <p className="truncate text-xs text-muted-foreground">{a.detail}</p>
                        )}
                        {a.at && (
                          <p className="text-xs text-muted-foreground">
                            {new Date(a.at).toLocaleString()}
                          </p>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
