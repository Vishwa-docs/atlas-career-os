import { Activity, BookOpen, CheckCircle2, AlertTriangle } from "lucide-react";
import { PageHeader, SectionHeading, EmptyState, Spinner } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatPercent } from "@/lib/utils";
import { useCurriculum, type CurriculumGap, type MarketSkill } from "../api";

function severityVariant(s?: CurriculumGap["severity"]): "destructive" | "warning" | "secondary" {
  if (s === "high") return "destructive";
  if (s === "medium") return "warning";
  return "secondary";
}

/** Heatmap-style coverage cell: market demand intensity vs how well it's covered. */
function CoverageRow({ skill }: { skill: MarketSkill }) {
  const demand = skill.demand ?? 0;
  const coverage = skill.coverage ?? 0;
  const gapped = coverage < 0.5 && demand >= 0.5;
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-lg border bg-card p-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{skill.skill}</p>
        <div className="mt-1.5 flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            Demand
            <span className="inline-block h-1.5 w-16 overflow-hidden rounded-full bg-muted">
              <span className="block h-full rounded-full bg-brand" style={{ width: `${demand * 100}%` }} />
            </span>
          </span>
          <span className="flex items-center gap-1.5">
            Covered
            <span className="inline-block h-1.5 w-16 overflow-hidden rounded-full bg-muted">
              <span
                className={cn("block h-full rounded-full", gapped ? "bg-warning" : "bg-success")}
                style={{ width: `${coverage * 100}%` }}
              />
            </span>
          </span>
        </div>
      </div>
      <span
        className={cn(
          "rounded-md px-2 py-1 text-xs font-medium tabular-nums",
          gapped ? "bg-warning/20 text-warning-foreground" : "bg-success/15 text-success",
        )}
      >
        {formatPercent(coverage)}
      </span>
    </div>
  );
}

export default function CurriculumEngine() {
  const { data, isLoading, isError } = useCurriculum();

  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Outcomes Studio" title="Curriculum Engine" />
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-96 rounded-xl" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
        <div className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> Mapping curriculum against the market…
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="animate-fade-in">
        <PageHeader eyebrow="Outcomes Studio" title="Curriculum Engine" />
        <EmptyState
          icon={Activity}
          title="Couldn't load curriculum analysis"
          description="We hit a snag mapping your curriculum. Please try again shortly."
        />
      </div>
    );
  }

  const marketSkills = data.market_skills ?? [];
  const covered = data.covered ?? [];
  const gaps = data.gaps ?? [];

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Outcomes Studio"
        title="Curriculum Engine"
        description={`Future-state curriculum mapping for ${data.program} — where the market is heading vs what you teach today.`}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardContent className="p-5">
            <SectionHeading
              title="Market skills coverage"
              description="In-demand skills and how well the curriculum covers them"
            />
            {marketSkills.length === 0 ? (
              <EmptyState
                icon={BookOpen}
                title="No market skills mapped"
                description="Skill demand data will appear here once the curriculum is analysed."
              />
            ) : (
              <div className="space-y-2">
                {marketSkills.map((s) => (
                  <CoverageRow key={s.skill} skill={s} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardContent className="p-5">
              <SectionHeading
                title="Coverage gaps"
                description="High-demand skills under-served by the curriculum"
              />
              {gaps.length === 0 ? (
                <EmptyState
                  icon={CheckCircle2}
                  title="No gaps detected"
                  description="Your curriculum covers the current in-demand skill set."
                />
              ) : (
                <ul className="space-y-3">
                  {gaps.map((g) => (
                    <li key={g.skill} className="flex gap-3 rounded-lg border border-warning/30 bg-warning/5 p-3">
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning-foreground" />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-medium">{g.skill}</p>
                          <Badge variant={severityVariant(g.severity)}>{g.severity ?? "gap"}</Badge>
                        </div>
                        {g.recommendation && (
                          <p className="mt-1 text-sm text-muted-foreground">{g.recommendation}</p>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-5">
              <SectionHeading title="Already covered" description="Skills well-served by the current curriculum" />
              {covered.length === 0 ? (
                <p className="text-sm text-muted-foreground">No coverage recorded yet.</p>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {covered.map((c) => (
                    <Badge key={c} variant="success" className="gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      {c}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <GlassBoxPanel glassBox={data.glass_box} title="How these gaps were identified" className="mt-6" />
    </div>
  );
}
