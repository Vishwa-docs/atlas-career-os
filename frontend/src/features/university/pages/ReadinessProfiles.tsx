import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Activity, Gauge, Target } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PageHeader, SectionHeading, EmptyState } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPercent } from "@/lib/utils";
import { useReadiness, useStudents, asArray, type UniversityStudent } from "../api";

export default function ReadinessProfiles() {
  const [searchParams, setSearchParams] = useSearchParams();
  const studentsQuery = useStudents();
  const students = useMemo(
    () => asArray<UniversityStudent>(studentsQuery.data),
    [studentsQuery.data],
  );

  const paramId = searchParams.get("student") ?? "";
  const [selected, setSelected] = useState(paramId);

  // Default to the first student once the roster loads, if none chosen.
  useEffect(() => {
    if (!selected && students.length > 0) setSelected(students[0].id);
  }, [selected, students]);

  const studentId = selected || paramId;
  const { data, isLoading, isError } = useReadiness(studentId || undefined);

  function onSelect(id: string) {
    setSelected(id);
    setSearchParams(id ? { student: id } : {});
  }

  const dimensions = data?.dimensions ?? [];
  const radarData = dimensions.map((d) => ({
    dimension: d.name,
    score: Math.round(d.score * 100),
    benchmark: d.benchmark != null ? Math.round(d.benchmark * 100) : undefined,
  }));
  const hasBenchmark = dimensions.some((d) => d.benchmark != null);

  const selectedName =
    data?.student_name ?? students.find((s) => s.id === studentId)?.full_name;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Outcomes Studio"
        title="Adaptive Readiness Profiles"
        description="A multi-dimensional, explainable view of how prepared each student is for the world of work."
      />

      <Card className="mb-6">
        <CardContent className="p-5">
          <div className="space-y-1.5 sm:max-w-sm">
            <Label htmlFor="student">Student</Label>
            <select
              id="student"
              value={studentId}
              onChange={(e) => onSelect(e.target.value)}
              disabled={studentsQuery.isLoading}
              className="flex h-10 w-full items-center justify-between rounded-lg border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-60"
            >
              {students.length === 0 && <option value="">No students yet</option>}
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name}
                  {s.program ? ` · ${s.program}` : ""}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {!studentId ? (
        <EmptyState
          icon={Target}
          title="Pick a student"
          description="Choose a student to see their explainable readiness profile."
        />
      ) : isLoading ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-80 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      ) : isError || !data ? (
        <EmptyState
          icon={Activity}
          title="Couldn't load readiness"
          description="We hit a snag computing this profile. Please try again shortly."
        />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardContent className="p-5">
                <div className="mb-4 flex items-center justify-between">
                  <SectionHeading
                    title="Readiness radar"
                    description={selectedName ? `${selectedName}'s strengths and gaps` : "Strengths and gaps"}
                  />
                  <div className="flex items-center gap-2 rounded-lg bg-accent/60 px-3 py-1.5">
                    <Gauge className="h-4 w-4 text-brand" />
                    <span className="font-display text-xl font-bold text-brand tabular-nums">
                      {formatPercent(data.score)}
                    </span>
                  </div>
                </div>
                {radarData.length === 0 ? (
                  <EmptyState icon={Target} title="No dimensions scored yet" />
                ) : (
                  <div className="h-80 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={radarData} outerRadius="72%">
                        <PolarGrid stroke="hsl(var(--border))" />
                        <PolarAngleAxis
                          dataKey="dimension"
                          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                        />
                        <PolarRadiusAxis
                          domain={[0, 100]}
                          tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                          axisLine={false}
                        />
                        {hasBenchmark && (
                          <Radar
                            name="Cohort benchmark"
                            dataKey="benchmark"
                            stroke="hsl(var(--muted-foreground))"
                            fill="hsl(var(--muted-foreground))"
                            fillOpacity={0.1}
                          />
                        )}
                        <Radar
                          name="Student"
                          dataKey="score"
                          stroke="hsl(var(--brand))"
                          fill="hsl(var(--brand))"
                          fillOpacity={0.35}
                        />
                        <RechartsTooltip
                          formatter={(v: number) => `${v}%`}
                          contentStyle={{
                            background: "hsl(var(--popover))",
                            border: "1px solid hsl(var(--border))",
                            borderRadius: 8,
                            fontSize: 12,
                          }}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-5">
                <SectionHeading
                  title="Dimensions"
                  description="Per-dimension readiness scores"
                />
                {radarData.length === 0 ? (
                  <EmptyState icon={Target} title="No dimensions scored yet" />
                ) : (
                  <div className="h-80 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={radarData}
                        layout="vertical"
                        margin={{ top: 4, right: 16, left: 8, bottom: 0 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                        <XAxis
                          type="number"
                          domain={[0, 100]}
                          tickFormatter={(v: number) => `${v}%`}
                          tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                          tickLine={false}
                          axisLine={false}
                        />
                        <YAxis
                          type="category"
                          dataKey="dimension"
                          width={120}
                          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                          tickLine={false}
                          axisLine={false}
                        />
                        <RechartsTooltip
                          formatter={(v: number) => [`${v}%`, "Score"]}
                          contentStyle={{
                            background: "hsl(var(--popover))",
                            border: "1px solid hsl(var(--border))",
                            borderRadius: 8,
                            fontSize: 12,
                          }}
                        />
                        <Bar dataKey="score" fill="hsl(var(--brand))" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <GlassBoxPanel glassBox={data.glass_box} title="How this readiness profile was assessed" />
        </div>
      )}
    </div>
  );
}
