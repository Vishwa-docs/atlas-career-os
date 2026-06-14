import { cn } from "@/lib/utils";

/** A compact circular match-score gauge used on job cards & detail. */
export function MatchRing({
  score,
  size = 56,
  className,
}: {
  score: number; // 0..1
  size?: number;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(1, score));
  const stroke = 5;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const tone =
    pct >= 0.75 ? "text-success" : pct >= 0.5 ? "text-brand" : "text-muted-foreground";
  return (
    <div className={cn("relative shrink-0", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          className="stroke-muted"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          className={cn("transition-all", tone)}
          stroke="currentColor"
        />
      </svg>
      <span
        className={cn(
          "absolute inset-0 flex items-center justify-center text-sm font-bold tabular-nums",
          tone,
        )}
      >
        {Math.round(pct * 100)}
      </span>
    </div>
  );
}

/** A small pill summarising a match score. */
export function MatchBadge({ score }: { score: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);
  const tone =
    pct >= 75
      ? "bg-success/15 text-success"
      : pct >= 50
        ? "bg-brand/15 text-brand"
        : "bg-muted text-muted-foreground";
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums", tone)}>
      {pct}% match
    </span>
  );
}
