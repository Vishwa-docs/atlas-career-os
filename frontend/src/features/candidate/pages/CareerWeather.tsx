import { useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Cloud,
  CloudRain,
  CloudSun,
  Snowflake,
  Sun,
  TrendingUp,
  Wind,
} from "lucide-react";
import { EmptyState, PageHeader, Spinner } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiClientError } from "@/lib/apiClient";
import { cn, formatPercent } from "@/lib/utils";
import { useWeather, type WeatherResponse } from "../api";

const OUTLOOK = {
  sunny: {
    label: "Sunny",
    Icon: Sun,
    gradient: "from-amber-400/30 via-warning/15 to-transparent",
    accent: "text-warning-foreground",
    blurb: "Strong, growing demand. A great time to push for more.",
  },
  cloudy: {
    label: "Cloudy",
    Icon: CloudSun,
    gradient: "from-slate-400/20 via-muted to-transparent",
    accent: "text-muted-foreground",
    blurb: "Steady but mixed signals. Differentiate to stand out.",
  },
  stormy: {
    label: "Stormy",
    Icon: CloudRain,
    gradient: "from-destructive/20 via-destructive/5 to-transparent",
    accent: "text-destructive",
    blurb: "Headwinds ahead. Consider adjacent moves and reskilling.",
  },
} as const;

export default function CareerWeather() {
  const [region, setRegion] = useState("");
  const weather = useWeather();
  const data = weather.data;

  function forecast() {
    weather.mutate({ region: region.trim() || undefined });
  }

  return (
    <div className="animate-fade-in space-y-8">
      <PageHeader
        eyebrow="Signature · Career Weather"
        title="The forecast for your field"
        description="A plain-language outlook for your occupation: demand, rising and cooling skills, and where pay is drifting."
        action={
          <div className="flex items-center gap-2">
            <Input
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              placeholder="Region (optional)"
              className="w-44"
              onKeyDown={(e) => e.key === "Enter" && forecast()}
            />
            <Button variant="brand" onClick={forecast} disabled={weather.isPending}>
              {weather.isPending ? <Spinner /> : <Cloud />} Get forecast
            </Button>
          </div>
        }
      />

      {weather.isPending && (
        <Card>
          <CardContent className="flex items-center justify-center gap-3 py-20 text-muted-foreground">
            <Spinner className="h-5 w-5 text-brand" /> Reading the market barometer…
          </CardContent>
        </Card>
      )}

      {weather.isError && !weather.isPending && (
        <EmptyState
          icon={CloudRain}
          title="Couldn't fetch the forecast"
          description={
            weather.error instanceof ApiClientError
              ? weather.error.message
              : "Something went wrong. Try again."
          }
          action={
            <Button variant="outline" onClick={forecast}>
              Retry
            </Button>
          }
        />
      )}

      {!weather.isPending && !data && !weather.isError && (
        <EmptyState
          icon={CloudSun}
          title="No forecast yet"
          description="Generate a forecast to see the outlook for your occupation."
          action={
            <Button variant="brand" onClick={forecast}>
              <Cloud /> Get forecast
            </Button>
          }
        />
      )}

      {data && !weather.isPending && <WeatherReport data={data} />}
    </div>
  );
}

function WeatherReport({ data }: { data: WeatherResponse }) {
  const meta = OUTLOOK[data.outlook] ?? OUTLOOK.cloudy;
  const Icon = meta.Icon;
  const drift = data.salary_drift_pct ?? 0;

  return (
    <div className="space-y-6">
      {/* Hero */}
      <Card className="overflow-hidden">
        <div className={cn("relative bg-gradient-to-br p-8", meta.gradient)}>
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-5">
              <Icon className={cn("h-16 w-16", meta.accent)} />
              <div>
                <p className="text-xs uppercase tracking-widest text-muted-foreground">
                  {data.role}
                  {data.region ? ` · ${data.region}` : ""}
                </p>
                <h2 className="font-display text-3xl font-bold tracking-tight">
                  {meta.label} outlook
                </h2>
                <p className="mt-1 max-w-md text-sm text-muted-foreground">{meta.blurb}</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="rounded-xl bg-card/80 px-4 py-3 text-center shadow-sm backdrop-blur">
                <p className="text-xs text-muted-foreground">Demand index</p>
                <p className="font-display text-2xl font-bold tabular-nums">{data.demand_index}</p>
              </div>
              <div className="rounded-xl bg-card/80 px-4 py-3 text-center shadow-sm backdrop-blur">
                <p className="text-xs text-muted-foreground">Salary drift</p>
                <p
                  className={cn(
                    "flex items-center justify-center gap-0.5 font-display text-2xl font-bold tabular-nums",
                    drift >= 0 ? "text-success" : "text-destructive",
                  )}
                >
                  {drift >= 0 ? (
                    <ArrowUpRight className="h-5 w-5" />
                  ) : (
                    <ArrowDownRight className="h-5 w-5" />
                  )}
                  {formatPercent(Math.abs(drift) / 100, 1)}
                </p>
              </div>
            </div>
          </div>
          {data.summary && (
            <p className="mt-6 max-w-3xl leading-relaxed text-foreground/90">{data.summary}</p>
          )}
        </div>
      </Card>

      {/* Skill winds */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardContent className="p-5">
            <p className="mb-3 flex items-center gap-2 font-semibold">
              <TrendingUp className="h-4 w-4 text-success" /> Rising skills
            </p>
            {data.rising_skills.length === 0 ? (
              <p className="text-sm text-muted-foreground">No rising signals detected.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {data.rising_skills.map((s) => (
                  <Badge key={s} variant="success" className="gap-1">
                    <ArrowUpRight className="h-3 w-3" /> {s}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="mb-3 flex items-center gap-2 font-semibold">
              <Snowflake className="h-4 w-4 text-muted-foreground" /> Cooling skills
            </p>
            {data.cooling_skills.length === 0 ? (
              <p className="text-sm text-muted-foreground">No cooling signals detected.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {data.cooling_skills.map((s) => (
                  <Badge key={s} variant="secondary" className="gap-1">
                    <Wind className="h-3 w-3" /> {s}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <GlassBoxPanel glassBox={data.glass_box} title="How Atlas read the weather" />
    </div>
  );
}
