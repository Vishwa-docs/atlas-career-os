import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Globe2, TrendingDown, TrendingUp } from "lucide-react";
import { PageHeader, SectionHeading, EmptyState } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPercent } from "@/lib/utils";
import { useWorkforce, type WorkforceScenario } from "../api";

function ScenarioCard({ scenario }: { scenario: WorkforceScenario }) {
  const positive = (scenario.delta_pct ?? 0) >= 0;
  return (
    <Card>
      <CardContent className="space-y-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <h4 className="text-sm font-semibold">{scenario.title}</h4>
          {scenario.delta_pct != null && (
            <span
              className={`flex shrink-0 items-center gap-1 text-xs font-medium ${
                positive ? "text-success" : "text-destructive"
              }`}
            >
              {positive ? (
                <TrendingUp className="h-3.5 w-3.5" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5" />
              )}
              {positive ? "+" : ""}
              {formatPercent(scenario.delta_pct)}
            </span>
          )}
        </div>
        {scenario.description && (
          <p className="text-sm text-muted-foreground">{scenario.description}</p>
        )}
        <div className="flex flex-wrap gap-1.5 pt-1">
          {scenario.horizon_years != null && (
            <Badge variant="outline">{scenario.horizon_years}y horizon</Badge>
          )}
          {scenario.impact && <Badge variant="secondary">{scenario.impact}</Badge>}
        </div>
      </CardContent>
    </Card>
  );
}

export default function WorkforceResilience() {
  const { data, isLoading, isError } = useWorkforce();

  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Talent Radar" title="Workforce resilience" />
        <Skeleton className="mb-6 h-80 rounded-xl" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Talent Radar" title="Workforce resilience" />
        <EmptyState
          icon={Globe2}
          title="Couldn't load workforce projections"
          description="We hit a snag fetching the resilience model. Please try again shortly."
        />
      </div>
    );
  }

  const projections = data.projections ?? [];
  const scenarios = data.scenarios ?? [];

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Talent Radar"
        title="Workforce resilience"
        description={`UN-WPP-based labour-supply outlook for ${data.country} — plan hiring against demographic reality.`}
        action={<Badge variant="warning">In progress</Badge>}
      />

      <Card className="mb-6">
        <CardContent className="p-5">
          <SectionHeading
            title="Working-age population projection"
            description="Working-age headcount and a relative labour-supply index over time"
          />
          {projections.length === 0 ? (
            <EmptyState
              icon={Globe2}
              title="No projection data"
              description="Demographic projections for your market will render here."
            />
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={projections} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="year"
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={12}
                    tickLine={false}
                  />
                  <YAxis
                    yAxisId="left"
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={12}
                    tickLine={false}
                    width={48}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={12}
                    tickLine={false}
                    width={40}
                  />
                  <RechartsTooltip
                    contentStyle={{
                      background: "hsl(var(--popover))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="working_age"
                    name="Working-age population"
                    stroke="hsl(var(--brand))"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="supply_index"
                    name="Supply index"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {scenarios.length > 0 && (
        <div className="mb-6">
          <SectionHeading title="Scenarios" description="How different levers shift your talent supply" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {scenarios.map((s) => (
              <ScenarioCard key={s.id} scenario={s} />
            ))}
          </div>
        </div>
      )}

      <GlassBoxPanel glassBox={data.glass_box} />
    </div>
  );
}
