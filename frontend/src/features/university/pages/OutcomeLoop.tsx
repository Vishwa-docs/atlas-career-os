import { Activity, Briefcase, LineChart as LineChartIcon, TrendingUp } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader, SectionHeading, StatCard, EmptyState, Spinner } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { useOutcomes } from "../api";

export default function OutcomeLoop() {
  const { data, isLoading, isError } = useOutcomes();

  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Outcomes Studio" title="Outcome Loop" />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <div className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> Computing outcome analytics…
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Outcomes Studio" title="Outcome Loop" />
        <EmptyState
          icon={Activity}
          title="Couldn't load outcomes"
          description="We hit a snag fetching outcome analytics. Please try again shortly."
        />
      </div>
    );
  }

  const currency = data.currency ?? "MYR";
  const byField = data.by_field ?? [];
  const trend = data.trend ?? [];

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Outcomes Studio"
        title="Outcome Loop"
        description="Close the loop between what you teach and where graduates land — employment, earnings and speed to first role."
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Employment rate"
          value={formatPercent(data.employment_rate)}
          icon={Briefcase}
          tone="success"
        />
        <StatCard
          label="Median salary"
          value={formatCurrency(data.median_salary, currency)}
          icon={TrendingUp}
          tone="brand"
        />
        <StatCard
          label="Months to employ"
          value={data.median_months_to_employ}
          hint="Median across cohorts"
          icon={Activity}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardContent className="p-5">
            <SectionHeading
              title="Employment rate by field"
              description="Share of graduates employed, per field of study"
            />
            {byField.length === 0 ? (
              <EmptyState
                icon={Briefcase}
                title="No field breakdown yet"
                description="Field-level outcomes appear once cohorts are tracked."
              />
            ) : (
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={byField} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                    <XAxis
                      type="number"
                      domain={[0, 1]}
                      tickFormatter={(v: number) => formatPercent(v)}
                      tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="field"
                      width={120}
                      tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <RechartsTooltip
                      formatter={(v: number) => [formatPercent(v), "Employed"]}
                      contentStyle={{
                        background: "hsl(var(--popover))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                    />
                    <Bar dataKey="employment_rate" fill="hsl(var(--brand))" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <SectionHeading
              title="Multi-year trend"
              description="Employment rate over graduating cohorts"
            />
            {trend.length === 0 ? (
              <EmptyState
                icon={LineChartIcon}
                title="No trend data yet"
                description="As more cohorts graduate, the multi-year trend appears here."
              />
            ) : (
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trend} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
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
                    <Line
                      type="monotone"
                      dataKey="employment_rate"
                      stroke="hsl(var(--brand))"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {data.glass_box && <GlassBoxPanel glassBox={data.glass_box} className="mt-6" defaultOpen={false} />}
    </div>
  );
}
