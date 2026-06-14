import {
  Activity,
  Award,
  Briefcase,
  GraduationCap,
  TrendingUp,
  Users,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader, SectionHeading, StatCard, EmptyState, Spinner } from "@/components/common";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { useUniversityDashboard } from "../api";

export default function Dashboard() {
  const { data, isLoading, isError } = useUniversityDashboard();

  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Outcomes Studio" title="University dashboard" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <div className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> Loading outcome metrics…
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Outcomes Studio" title="University dashboard" />
        <EmptyState
          icon={Activity}
          title="Couldn't load your dashboard"
          description="We hit a snag fetching your outcome metrics. Please try again shortly."
        />
      </div>
    );
  }

  const currency = data.currency ?? "MYR";
  const trend = data.trend ?? [];

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Outcomes Studio"
        title="University dashboard"
        description="Graduate outcomes at a glance — employment, earnings and time-to-employ across your cohorts."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Employment rate"
          value={formatPercent(data.employment_rate)}
          hint="Graduates employed within 6 months"
          icon={Briefcase}
          tone="success"
        />
        <StatCard
          label="Median starting salary"
          value={formatCurrency(data.median_salary, currency)}
          icon={TrendingUp}
          tone="brand"
        />
        <StatCard
          label="Months to employ"
          value={data.median_months_to_employ}
          hint="Median, post-graduation"
          icon={Activity}
        />
        <StatCard
          label="Active students"
          value={data.active_students}
          hint={
            data.graduates_tracked != null
              ? `${data.graduates_tracked} graduates tracked`
              : undefined
          }
          icon={Users}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <Card>
            <CardContent className="p-5">
              <SectionHeading
                title="Employment rate trend"
                description="Share of graduates in work, by graduating year"
              />
              {trend.length === 0 ? (
                <EmptyState
                  icon={TrendingUp}
                  title="No trend data yet"
                  description="As cohorts graduate and outcomes are tracked, your trend line will appear here."
                />
              ) : (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trend} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
                      <defs>
                        <linearGradient id="emp" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--brand))" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="hsl(var(--brand))" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                      <XAxis
                        dataKey="year"
                        tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        domain={[0, 1]}
                        tickFormatter={(v: number) => formatPercent(v)}
                        tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                        tickLine={false}
                        axisLine={false}
                        width={48}
                      />
                      <RechartsTooltip
                        formatter={(v: number) => [formatPercent(v), "Employment"]}
                        contentStyle={{
                          background: "hsl(var(--popover))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: 8,
                          fontSize: 12,
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="employment_rate"
                        stroke="hsl(var(--brand))"
                        strokeWidth={2}
                        fill="url(#emp)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <Card className="h-full">
            <CardContent className="p-5">
              <SectionHeading title="Programs at a glance" description="Your Outcomes Studio footprint" />
              <ul className="divide-y">
                <li className="flex items-center justify-between py-3">
                  <span className="flex items-center gap-2 text-sm text-muted-foreground">
                    <GraduationCap className="h-4 w-4 text-brand" /> Programs tracked
                  </span>
                  <span className="font-display text-lg font-semibold tabular-nums">
                    {data.programs ?? "—"}
                  </span>
                </li>
                <li className="flex items-center justify-between py-3">
                  <span className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Briefcase className="h-4 w-4 text-brand" /> Internships open
                  </span>
                  <span className="font-display text-lg font-semibold tabular-nums">
                    {data.internships_open ?? "—"}
                  </span>
                </li>
                <li className="flex items-center justify-between py-3">
                  <span className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Award className="h-4 w-4 text-brand" /> Credentials issued
                  </span>
                  <span className="font-display text-lg font-semibold tabular-nums">
                    {data.credentials_issued ?? "—"}
                  </span>
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
