import { useState } from "react";
import {
  Clock,
  Compass,
  Gauge,
  MapPin,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import { EmptyState, PageHeader, Spinner } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiClientError } from "@/lib/apiClient";
import { cn, formatCurrency, formatPercent } from "@/lib/utils";
import { useAtlas, type AtlasRoute } from "../api";

const HORIZONS = [3, 5, 10];

export default function TrajectoryAtlas() {
  const [horizon, setHorizon] = useState(5);
  const [selected, setSelected] = useState<string | null>(null);
  const atlas = useAtlas();
  const data = atlas.data;

  function generate(years: number) {
    setHorizon(years);
    setSelected(null);
    atlas.mutate(
      { horizon_years: years },
      { onSuccess: (d) => setSelected(d.routes[0]?.id ?? null) },
    );
  }

  return (
    <div className="animate-fade-in space-y-8">
      <PageHeader
        eyebrow="Signature · Trajectory Atlas"
        title="Where could you go?"
        description="Atlas charts plausible career routes from where you are today — each with salary, time-to-reach, feasibility, and the skills you'd need to close."
        action={
          <div className="flex items-center gap-2">
            <Select value={String(horizon)} onValueChange={(v) => setHorizon(Number(v))}>
              <SelectTrigger className="w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {HORIZONS.map((h) => (
                  <SelectItem key={h} value={String(h)}>
                    {h}-year horizon
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="brand" onClick={() => generate(horizon)} disabled={atlas.isPending}>
              {atlas.isPending ? <Spinner /> : <Compass />} Chart my atlas
            </Button>
          </div>
        }
      />

      {atlas.isPending && (
        <Card>
          <CardContent className="flex items-center justify-center gap-3 py-20 text-muted-foreground">
            <Spinner className="h-5 w-5 text-brand" />
            Mapping {horizon}-year routes across the Career Graph…
          </CardContent>
        </Card>
      )}

      {atlas.isError && !atlas.isPending && (
        <EmptyState
          icon={Compass}
          title="Couldn't chart your atlas"
          description={
            atlas.error instanceof ApiClientError
              ? atlas.error.message
              : "Something went wrong. Try again."
          }
          action={
            <Button variant="outline" onClick={() => generate(horizon)}>
              Retry
            </Button>
          }
        />
      )}

      {!atlas.isPending && !data && !atlas.isError && (
        <EmptyState
          icon={Compass}
          title="Your atlas is unmapped"
          description="Pick a horizon and chart your atlas to see where your trajectory could lead."
          action={
            <Button variant="brand" onClick={() => generate(horizon)}>
              <Compass /> Chart my atlas
            </Button>
          }
        />
      )}

      {data && !atlas.isPending && (
        <div className="space-y-6">
          {/* Origin */}
          <div className="flex items-center gap-3 rounded-xl border bg-gradient-to-r from-primary/10 to-transparent p-4">
            <div className="rounded-full bg-card p-2.5 shadow-sm">
              <MapPin className="h-5 w-5 text-brand" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">You are here</p>
              <p className="font-display text-lg font-semibold">{data.current.occupation}</p>
            </div>
            <Badge variant="brand" className="ml-auto">
              {data.routes.length} route{data.routes.length === 1 ? "" : "s"} charted
            </Badge>
          </div>

          {/* Constellation of routes */}
          {data.routes.length === 0 ? (
            <EmptyState
              icon={Compass}
              title="No routes found for this horizon"
              description="Try a longer horizon or enrich your profile with more skills and aspirations."
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {data.routes.map((r, i) => (
                <RouteCard
                  key={r.id}
                  route={r}
                  index={i}
                  active={selected === r.id}
                  onSelect={() => setSelected(r.id)}
                />
              ))}
            </div>
          )}

          {/* Detail of selected route */}
          {selected &&
            (() => {
              const r = data.routes.find((x) => x.id === selected);
              return r ? <RouteDetail route={r} /> : null;
            })()}

          <GlassBoxPanel glassBox={data.glass_box} title="How Atlas charted these routes" />
        </div>
      )}
    </div>
  );
}

function feasibilityTone(f: number) {
  if (f >= 0.66) return { label: "High feasibility", className: "text-success", bar: "bg-success" };
  if (f >= 0.4) return { label: "Moderate", className: "text-warning-foreground", bar: "bg-warning" };
  return { label: "A stretch", className: "text-muted-foreground", bar: "bg-muted-foreground" };
}

function RouteCard({
  route,
  index,
  active,
  onSelect,
}: {
  route: AtlasRoute;
  index: number;
  active: boolean;
  onSelect: () => void;
}) {
  const feas = feasibilityTone(route.feasibility);
  const sr = route.salary_range;
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "group relative overflow-hidden rounded-2xl border bg-card p-5 text-left shadow-sm transition-all hover:shadow-lg",
        active ? "border-brand ring-2 ring-brand/30" : "hover:border-brand/40",
      )}
    >
      <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-gradient-to-br from-brand/20 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="flex items-start justify-between gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent text-xs font-bold text-brand">
          {index + 1}
        </span>
        {route.demand_trend !== 0 && (
          <Badge variant={route.demand_trend > 0 ? "success" : "secondary"} className="gap-1">
            <TrendingUp className="h-3 w-3" />
            {route.demand_trend > 0 ? "+" : ""}
            {formatPercent(route.demand_trend, 0)} demand
          </Badge>
        )}
      </div>

      <h3 className="mt-3 font-display text-lg font-semibold leading-tight">{route.title}</h3>

      <p className="mt-2 font-semibold tabular-nums">
        {formatCurrency(sr.min, sr.currency)}–{formatCurrency(sr.max, sr.currency)}
        {sr.median ? (
          <span className="ml-1 text-xs font-normal text-muted-foreground">
            · median {formatCurrency(sr.median, sr.currency)}
          </span>
        ) : null}
      </p>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <Clock className="h-3.5 w-3.5" />
          {route.time_months.min}–{route.time_months.max} months
        </span>
        <span className="flex items-center gap-1">
          <Target className="h-3.5 w-3.5" />
          {route.skill_gaps.length} skill gap{route.skill_gaps.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="flex items-center gap-1 text-muted-foreground">
            <Gauge className="h-3.5 w-3.5" /> Feasibility
          </span>
          <span className={cn("font-medium", feas.className)}>
            {feas.label} · {formatPercent(route.feasibility)}
          </span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn("h-full rounded-full", feas.bar)}
            style={{ width: `${route.feasibility * 100}%` }}
          />
        </div>
      </div>
    </button>
  );
}

function RouteDetail({ route }: { route: AtlasRoute }) {
  return (
    <Card className="border-brand/30">
      <CardContent className="space-y-5 p-6">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-brand" />
          <h3 className="font-display text-lg font-semibold">{route.title}</h3>
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          {/* Skill gaps */}
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Skill gaps to close
            </p>
            {route.skill_gaps.length === 0 ? (
              <p className="text-sm text-muted-foreground">No major gaps — you're ready.</p>
            ) : (
              <div className="space-y-2.5">
                {route.skill_gaps.map((g) => (
                  <div key={g.skill}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span>{g.skill}</span>
                      <span className="text-xs text-muted-foreground tabular-nums">
                        {formatPercent(g.have)} → {formatPercent(g.need)}
                      </span>
                    </div>
                    <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className="absolute h-full rounded-full bg-muted-foreground/40"
                        style={{ width: `${g.need * 100}%` }}
                      />
                      <div
                        className="absolute h-full rounded-full bg-brand"
                        style={{ width: `${g.have * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Trade-offs */}
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Trade-offs to weigh
            </p>
            {route.trade_offs.length === 0 ? (
              <p className="text-sm text-muted-foreground">No notable trade-offs flagged.</p>
            ) : (
              <ul className="space-y-1.5 text-sm">
                {route.trade_offs.map((t, i) => (
                  <li key={i} className="flex gap-2 text-foreground/80">
                    <span className="text-brand">•</span>
                    {t}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <GlassBoxPanel glassBox={route.glass_box} title={`Why this route — ${route.title}`} />
      </CardContent>
    </Card>
  );
}
