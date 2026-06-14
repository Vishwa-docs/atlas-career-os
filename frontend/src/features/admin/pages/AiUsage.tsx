import { Activity, Coins, Cpu, DollarSign, Hash } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader, SectionHeading, StatCard, EmptyState } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency } from "@/lib/utils";
import { useAiUsage } from "../api";

const PALETTE = [
  "hsl(var(--brand))",
  "hsl(var(--primary))",
  "hsl(var(--success))",
  "hsl(var(--warning))",
  "hsl(var(--muted-foreground))",
  "hsl(var(--destructive))",
];

const TOOLTIP_STYLE = {
  background: "hsl(var(--popover))",
  border: "1px solid hsl(var(--border))",
  borderRadius: 8,
  fontSize: 12,
} as const;

const usd = (v: number) => formatCurrency(v, "USD", "en-US");

function compactTokens(v: number) {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}k`;
  return `${v}`;
}

function prettyFeature(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function AiUsage() {
  const { data, isLoading, isError } = useAiUsage();

  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Mission Control" title="AI cost ledger" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-80 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Mission Control" title="AI cost ledger" />
        <EmptyState
          icon={Activity}
          title="Couldn't load AI usage"
          description="We hit a snag fetching the cost ledger. Please try again shortly."
        />
      </div>
    );
  }

  const byFeature = (data.by_feature ?? [])
    .slice()
    .sort((a, b) => b.cost_usd - a.cost_usd)
    .map((f) => ({ ...f, feature: prettyFeature(f.feature) }));
  const byDay = data.by_day ?? [];

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Mission Control"
        title="AI cost ledger"
        description="Every ringgit and token spent on Atlas intelligence — broken down by feature and by day."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total cost"
          value={usd(data.total_cost_usd)}
          hint="Across all AI features"
          icon={DollarSign}
          tone="warning"
        />
        <StatCard
          label="Total tokens"
          value={compactTokens(data.tokens)}
          hint={data.tokens.toLocaleString() + " tokens"}
          icon={Hash}
        />
        <StatCard
          label="AI calls"
          value={(data.total_calls ?? 0).toLocaleString()}
          icon={Cpu}
          tone="brand"
        />
        <StatCard
          label="Avg cost / call"
          value={data.total_calls ? usd(data.total_cost_usd / data.total_calls) : "—"}
          hint={
            data.prompt_tokens != null && data.completion_tokens != null
              ? `${compactTokens(data.prompt_tokens)} in · ${compactTokens(data.completion_tokens)} out`
              : undefined
          }
          icon={Coins}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardContent className="p-5">
            <SectionHeading title="Cost by feature" description="Where the AI budget goes" />
            {byFeature.length === 0 ? (
              <EmptyState icon={Cpu} title="No feature usage yet" />
            ) : (
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={byFeature}
                    layout="vertical"
                    margin={{ top: 4, right: 16, left: 8, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v: number) => usd(v)}
                    />
                    <YAxis
                      type="category"
                      dataKey="feature"
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      tickLine={false}
                      axisLine={false}
                      width={120}
                    />
                    <RechartsTooltip
                      cursor={{ fill: "hsl(var(--muted))" }}
                      contentStyle={TOOLTIP_STYLE}
                      formatter={(v: number) => [usd(v), "Cost"]}
                    />
                    <Bar dataKey="cost_usd" name="Cost" radius={[0, 4, 4, 0]} barSize={20}>
                      {byFeature.map((_, i) => (
                        <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <SectionHeading title="Daily spend" description="Cost trend over time" />
            {byDay.length === 0 ? (
              <EmptyState icon={Activity} title="No daily data yet" />
            ) : (
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={byDay} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      tickLine={false}
                      axisLine={false}
                      minTickGap={24}
                      tickFormatter={(d: string) =>
                        new Date(d).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                      }
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      tickLine={false}
                      axisLine={false}
                      width={56}
                      tickFormatter={(v: number) => usd(v)}
                    />
                    <RechartsTooltip
                      contentStyle={TOOLTIP_STYLE}
                      formatter={(v: number) => [usd(v), "Cost"]}
                      labelFormatter={(d: string) => new Date(d).toLocaleDateString()}
                    />
                    <Line
                      type="monotone"
                      dataKey="cost_usd"
                      name="Cost"
                      stroke="hsl(var(--brand))"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {data.glass_box && (
        <div className="mt-6">
          <GlassBoxPanel
            glassBox={data.glass_box}
            title="How these costs are attributed"
            defaultOpen={false}
          />
        </div>
      )}
    </div>
  );
}
