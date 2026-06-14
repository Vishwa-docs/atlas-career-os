/**
 * GlassBoxPanel — the universal "why" surface.
 *
 * Atlas never shows a black-box score. Every AI judgement returns a `GlassBox`
 * (rationale + confidence + citations + what-would-change-this + caveats), and
 * this component renders it consistently so users always understand the
 * reasoning and where the uncertainty sits.
 */

import { useState } from "react";
import { ChevronDown, Info, Quote, Sparkles, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn, formatPercent } from "@/lib/utils";
import type { Confidence, GlassBox } from "@/types/api";

const confidenceMeta: Record<Confidence, { label: string; className: string; bar: string }> = {
  high: { label: "High confidence", className: "text-success", bar: "bg-success" },
  medium: { label: "Moderate confidence", className: "text-warning-foreground", bar: "bg-warning" },
  low: { label: "Low confidence", className: "text-muted-foreground", bar: "bg-muted-foreground" },
};

export function ConfidenceMeter({
  confidence,
  score,
  className,
}: {
  confidence: Confidence;
  score: number;
  className?: string;
}) {
  const meta = confidenceMeta[confidence];
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
        <div className={cn("h-full rounded-full", meta.bar)} style={{ width: `${score * 100}%` }} />
      </div>
      <span className={cn("text-xs font-medium", meta.className)}>
        {meta.label} · {formatPercent(score)}
      </span>
    </div>
  );
}

export function GlassBoxPanel({
  glassBox,
  title = "Why Atlas says this",
  defaultOpen = true,
  className,
}: {
  glassBox: GlassBox;
  title?: string;
  defaultOpen?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div
      className={cn(
        "rounded-xl border border-primary/20 bg-accent/40 text-sm",
        className,
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2 font-medium text-accent-foreground">
          <Sparkles className="h-4 w-4 text-brand" />
          {title}
        </span>
        <span className="flex items-center gap-3">
          <ConfidenceMeter confidence={glassBox.confidence} score={glassBox.confidence_score} />
          <ChevronDown
            className={cn("h-4 w-4 transition-transform", open && "rotate-180")}
          />
        </span>
      </button>

      {open && (
        <div className="space-y-4 px-4 pb-4">
          <p className="leading-relaxed text-foreground/90">{glassBox.rationale}</p>

          {glassBox.citations.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Evidence
              </p>
              <TooltipProvider delayDuration={150}>
                <div className="flex flex-wrap gap-1.5">
                  {glassBox.citations.map((c, i) => (
                    <Tooltip key={i}>
                      <TooltipTrigger asChild>
                        <span>
                          <Badge variant="outline" className="cursor-help gap-1">
                            <Quote className="h-3 w-3" />
                            {c.label}
                          </Badge>
                        </span>
                      </TooltipTrigger>
                      {c.snippet && <TooltipContent>{c.snippet}</TooltipContent>}
                    </Tooltip>
                  ))}
                </div>
              </TooltipProvider>
            </div>
          )}

          {glassBox.what_would_change_this.length > 0 && (
            <div>
              <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <TrendingUp className="h-3.5 w-3.5" /> What would change this
              </p>
              <ul className="space-y-1">
                {glassBox.what_would_change_this.map((w, i) => (
                  <li key={i} className="flex gap-2 text-foreground/80">
                    <span className="text-brand">→</span>
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {glassBox.caveats.length > 0 && (
            <div className="flex gap-2 rounded-lg bg-muted/60 p-3 text-xs text-muted-foreground">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <ul className="space-y-1">
                {glassBox.caveats.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
