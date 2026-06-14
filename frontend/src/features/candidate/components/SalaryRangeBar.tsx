import { formatCurrency } from "@/lib/utils";

/**
 * A market salary range bar: p25 → p75 with a p50 median tick and an optional
 * "you" marker. Used by Fair Pay and the Trajectory Atlas route cards.
 */
export function SalaryRangeBar({
  p25,
  p50,
  p75,
  currency = "MYR",
  you,
  compact,
}: {
  p25: number;
  p50: number;
  p75: number;
  currency?: string;
  you?: number;
  compact?: boolean;
}) {
  const lo = Math.min(p25, you ?? p25);
  const hi = Math.max(p75, you ?? p75);
  const span = Math.max(1, hi - lo);
  const pos = (v: number) => `${((v - lo) / span) * 100}%`;

  return (
    <div className={compact ? "" : "space-y-2"}>
      <div className="relative h-2.5 rounded-full bg-muted">
        <div
          className="absolute h-2.5 rounded-full bg-gradient-to-r from-brand/40 via-brand/70 to-brand"
          style={{ left: pos(p25), right: `calc(100% - ${pos(p75)})` }}
        />
        {/* median tick */}
        <div
          className="absolute top-1/2 h-4 w-0.5 -translate-y-1/2 rounded bg-foreground"
          style={{ left: pos(p50) }}
          aria-label="median"
        />
        {you != null && (
          <div
            className="absolute -top-1 h-4.5 w-4.5 -translate-x-1/2 rounded-full border-2 border-background bg-warning shadow"
            style={{ left: pos(you), height: 18, width: 18 }}
            aria-label="your pay"
          />
        )}
      </div>
      {!compact && (
        <div className="flex justify-between text-xs text-muted-foreground tabular-nums">
          <span>p25 {formatCurrency(p25, currency)}</span>
          <span className="font-medium text-foreground">p50 {formatCurrency(p50, currency)}</span>
          <span>p75 {formatCurrency(p75, currency)}</span>
        </div>
      )}
    </div>
  );
}
