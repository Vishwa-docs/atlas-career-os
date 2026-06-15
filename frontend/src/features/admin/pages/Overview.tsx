import {
  Activity,
  Briefcase,
  Building2,
  Cpu,
  DollarSign,
  GraduationCap,
  Users,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader, SectionHeading, StatCard, EmptyState } from "@/components/common";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency } from "@/lib/utils";
import { useAdminMetrics, type AdminBreakdown } from "../api";

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

function prettyLabel(s: string) {
  return s
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function BreakdownCard({
  title,
  description,
  data,
}: {
  title: string;
  description: string;
  data: AdminBreakdown[];
}) {
  const chartData = data.map((d) => ({ ...d, label: prettyLabel(d.label) }));
  return (
    <Card className="h-full">
      <CardContent className="p-5">
        <SectionHeading title={title} description={description} />
        {chartData.length === 0 ? (
          <EmptyState icon={Activity} title="No data yet" />
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 4, right: 16, left: 8, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <YAxis
                  type="category"
                  dataKey="label"
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  tickLine={false}
                  axisLine={false}
                  width={110}
                />
                <RechartsTooltip cursor={{ fill: "hsl(var(--muted))" }} contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="value" name="Count" radius={[0, 4, 4, 0]} barSize={18}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function Overview() {
  const { data, isLoading, isError } = useAdminMetrics();

  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Mission Control" title="Platform overview" />
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
        <PageHeader eyebrow="Mission Control" title="Platform overview" />
        <EmptyState
          icon={Activity}
          title="Couldn't load platform metrics"
          description="We hit a snag fetching the KPIs. Please try again shortly."
        />
      </div>
    );
  }

  const byRole = data.signups_by_role;
  const byType = data.orgs_by_type;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Mission Control"
        title="Platform overview"
        description="The state of Atlas at a glance — growth, organizations, and AI spend across all tenants."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total users"
          value={data.total_users.toLocaleString()}
          hint={`${data.candidates.toLocaleString()} candidates`}
          icon={Users}
          tone="brand"
        />
        <StatCard
          label="Organizations"
          value={data.total_orgs.toLocaleString()}
          hint={`${data.employers.toLocaleString()} employers · ${data.universities.toLocaleString()} universities`}
          icon={Building2}
        />
        <StatCard
          label="Open jobs"
          value={data.total_jobs.toLocaleString()}
          hint={`${data.total_applications.toLocaleString()} applications`}
          icon={Briefcase}
        />
        <StatCard
          label="AI spend"
          value={formatCurrency(data.ai_cost_usd_30d, "USD", "en-US")}
          hint={`${data.ai_calls_30d.toLocaleString()} AI calls`}
          icon={DollarSign}
          tone="warning"
        />
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Candidates" value={data.candidates.toLocaleString()} icon={Users} />
        <StatCard label="Employers" value={data.employers.toLocaleString()} icon={Building2} />
        <StatCard label="Universities" value={data.universities.toLocaleString()} icon={GraduationCap} />
        <StatCard label="AI calls" value={data.ai_calls_30d.toLocaleString()} icon={Cpu} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <BreakdownCard
          title="Signups by role"
          description="Who's joining the platform"
          data={byRole}
        />
        <BreakdownCard
          title="Organizations by type"
          description="Tenant mix across employers and universities"
          data={byType}
        />
      </div>
    </div>
  );
}
