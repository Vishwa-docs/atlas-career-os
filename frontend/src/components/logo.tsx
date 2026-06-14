import { cn } from "@/lib/utils";

/** The Atlas mark: a compass star inside a soft orbit — navigation, not prediction. */
export function AtlasLogo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("h-8 w-8", className)} aria-hidden="true">
      <defs>
        <linearGradient id="atlas-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="hsl(245 58% 51%)" />
          <stop offset="100%" stopColor="hsl(265 84% 60%)" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="14" fill="none" stroke="url(#atlas-grad)" strokeWidth="1.5" opacity="0.4" />
      <path
        d="M16 3 L19 13 L29 16 L19 19 L16 29 L13 19 L3 16 L13 13 Z"
        fill="url(#atlas-grad)"
      />
    </svg>
  );
}

export function AtlasWordmark({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <AtlasLogo className="h-7 w-7" />
      <span className="font-display text-lg font-bold tracking-tight">
        Atlas
        <span className="ml-1 text-xs font-medium text-muted-foreground">Career OS</span>
      </span>
    </div>
  );
}
