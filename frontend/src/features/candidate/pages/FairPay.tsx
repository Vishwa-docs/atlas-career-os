import { useState } from "react";
import { toast } from "sonner";
import {
  CheckCircle2,
  ClipboardCopy,
  Clock,
  MessageSquareQuote,
  Scale,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { EmptyState, PageHeader, Spinner } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiClientError } from "@/lib/apiClient";
import { cn, formatCurrency, formatPercent } from "@/lib/utils";
import { SalaryRangeBar } from "../components/SalaryRangeBar";
import { useFairPay, type FairPayResponse } from "../api";

export default function FairPay() {
  const [pay, setPay] = useState("");
  const fairPay = useFairPay();
  const data = fairPay.data;

  function analyze() {
    const parsed = pay ? Number(pay.replace(/[^\d.]/g, "")) : undefined;
    fairPay.mutate({ current_pay: parsed && parsed > 0 ? parsed : undefined });
  }

  return (
    <div className="animate-fade-in space-y-8">
      <PageHeader
        eyebrow="Signature · Fair Pay"
        title="Are you paid fairly?"
        description="See your pay against the live market range — and get a negotiation script grounded in the data."
        action={
          <div className="flex items-end gap-2">
            <div className="space-y-1">
              <Label htmlFor="pay" className="text-xs">
                Your current pay (optional)
              </Label>
              <Input
                id="pay"
                value={pay}
                onChange={(e) => setPay(e.target.value)}
                placeholder="e.g. 90000"
                inputMode="numeric"
                className="w-44"
                onKeyDown={(e) => e.key === "Enter" && analyze()}
              />
            </div>
            <Button variant="brand" onClick={analyze} disabled={fairPay.isPending}>
              {fairPay.isPending ? <Spinner /> : <Scale />} Analyze
            </Button>
          </div>
        }
      />

      {fairPay.isPending && (
        <Card>
          <CardContent className="flex items-center justify-center gap-3 py-20 text-muted-foreground">
            <Spinner className="h-5 w-5 text-brand" /> Benchmarking against the market…
          </CardContent>
        </Card>
      )}

      {fairPay.isError && !fairPay.isPending && (
        <EmptyState
          icon={Scale}
          title="Couldn't run the analysis"
          description={
            fairPay.error instanceof ApiClientError
              ? fairPay.error.message
              : "Something went wrong. Try again."
          }
          action={
            <Button variant="outline" onClick={analyze}>
              Retry
            </Button>
          }
        />
      )}

      {!fairPay.isPending && !data && !fairPay.isError && (
        <EmptyState
          icon={Scale}
          title="No analysis yet"
          description="Enter your pay (or leave blank) and analyze to benchmark your role against the market."
          action={
            <Button variant="brand" onClick={analyze}>
              <Scale /> Analyze my pay
            </Button>
          }
        />
      )}

      {data && !fairPay.isPending && <FairPayReport data={data} />}
    </div>
  );
}

function FairPayReport({ data }: { data: FairPayResponse }) {
  const { market } = data;
  const gap = data.gap_pct ?? 0;
  const underpaid = gap < 0;

  function copyScript() {
    navigator.clipboard
      .writeText(data.negotiation.script)
      .then(() => toast.success("Negotiation script copied"))
      .catch(() => toast.error("Couldn't copy"));
  }

  return (
    <div className="space-y-6">
      {/* Range bar hero */}
      <Card>
        <CardContent className="space-y-5 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                {data.role} · {data.location}
              </p>
              <h2 className="font-display text-xl font-semibold">Market pay range</h2>
            </div>
            {data.gap_pct != null && (
              <Badge
                variant={underpaid ? "warning" : "success"}
                className="gap-1 px-3 py-1 text-sm"
              >
                {underpaid ? (
                  <TrendingDown className="h-4 w-4" />
                ) : (
                  <TrendingUp className="h-4 w-4" />
                )}
                {underpaid ? "" : "+"}
                {formatPercent(gap / 100, 1)} vs median
              </Badge>
            )}
          </div>

          <SalaryRangeBar
            p25={market.p25}
            p50={market.p50}
            p75={market.p75}
            currency={market.currency}
            you={data.your_pay}
          />

          <div className="grid gap-3 sm:grid-cols-3">
            <Stat label="25th percentile" value={formatCurrency(market.p25, market.currency)} />
            <Stat
              label="Median (p50)"
              value={formatCurrency(market.p50, market.currency)}
              highlight
            />
            <Stat label="75th percentile" value={formatCurrency(market.p75, market.currency)} />
          </div>

          {data.your_pay != null && (
            <div className="flex items-center gap-2 rounded-lg bg-warning/10 p-3 text-sm">
              <span className="h-3 w-3 rounded-full bg-warning" />
              Your pay: <span className="font-semibold">{formatCurrency(data.your_pay, market.currency)}</span>
            </div>
          )}

          <div className="rounded-xl border border-brand/20 bg-accent/40 p-4">
            <p className="flex items-center gap-2 font-semibold">
              <Scale className="h-4 w-4 text-brand" /> Verdict
            </p>
            <p className="mt-1 leading-relaxed text-foreground/90">{data.verdict}</p>
          </div>
        </CardContent>
      </Card>

      {/* Negotiation */}
      <Card>
        <CardContent className="space-y-5 p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 font-display text-lg font-semibold">
              <MessageSquareQuote className="h-5 w-5 text-brand" /> Your negotiation playbook
            </h2>
            {data.negotiation.timing && (
              <Badge variant="brand" className="gap-1">
                <Clock className="h-3 w-3" /> {data.negotiation.timing}
              </Badge>
            )}
          </div>

          <div className="relative rounded-xl border bg-muted/40 p-4">
            <p className="whitespace-pre-wrap pr-10 text-sm italic leading-relaxed text-foreground/90">
              “{data.negotiation.script}”
            </p>
            <Button
              size="icon"
              variant="ghost"
              className="absolute right-2 top-2 h-8 w-8"
              onClick={copyScript}
              aria-label="Copy script"
            >
              <ClipboardCopy className="h-4 w-4" />
            </Button>
          </div>

          {data.negotiation.talking_points.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Talking points
              </p>
              <ul className="space-y-2">
                {data.negotiation.talking_points.map((p, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      <GlassBoxPanel glassBox={data.glass_box} title="How Atlas benchmarked your pay" />
    </div>
  );
}

function Stat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border p-3",
        highlight ? "border-brand/30 bg-accent/40" : "bg-card",
      )}
    >
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-display text-lg font-bold tabular-nums">{value}</p>
    </div>
  );
}
