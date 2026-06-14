import { toast } from "sonner";
import { AlertTriangle, Check, FileText, Radar } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useSignals,
  useUpdateSignal,
  asArray,
  type RetentionSignal,
  type SignalStatus,
} from "../api";

const SEVERITY_BADGE: Record<string, "warning" | "destructive" | "secondary"> = {
  high: "destructive",
  medium: "warning",
  low: "secondary",
};

function SignalCard({ signal }: { signal: RetentionSignal }) {
  const update = useUpdateSignal();
  const resolved = signal.status === "acknowledged" || signal.status === "actioned";

  function setStatus(status: SignalStatus) {
    update.mutate(
      { id: signal.id, status },
      {
        onSuccess: () => toast.success(`Signal ${status}`),
        onError: () => toast.error("Couldn't update the signal."),
      },
    );
  }

  return (
    <Card className={resolved ? "opacity-70" : undefined}>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold">{signal.title}</h3>
              {signal.severity && (
                <Badge variant={SEVERITY_BADGE[signal.severity] ?? "secondary"}>
                  {signal.severity}
                </Badge>
              )}
              {signal.type && <Badge variant="outline">{signal.type}</Badge>}
            </div>
            {signal.subject_name && (
              <p className="mt-1 text-sm text-muted-foreground">{signal.subject_name}</p>
            )}
          </div>
          {signal.status && signal.status !== "open" && (
            <Badge variant="success" className="shrink-0 capitalize">
              {signal.status}
            </Badge>
          )}
        </div>

        {signal.summary && <p className="text-sm text-foreground/90">{signal.summary}</p>}

        {signal.evidence && signal.evidence.length > 0 && (
          <div>
            <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <FileText className="h-3.5 w-3.5" /> Evidence
            </p>
            <ul className="space-y-1.5">
              {signal.evidence.map((e, i) => (
                <li key={i} className="flex gap-2 text-sm text-foreground/80">
                  <span className="text-brand">•</span>
                  <span>
                    <span className="font-medium">{e.label}</span>
                    {e.detail ? ` — ${e.detail}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <GlassBoxPanel glassBox={signal.glass_box} defaultOpen={false} />

        {!resolved && (
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={update.isPending}
              onClick={() => setStatus("acknowledged")}
            >
              <Check className="h-4 w-4" /> Acknowledge
            </Button>
            <Button
              size="sm"
              variant="brand"
              disabled={update.isPending}
              onClick={() => setStatus("actioned")}
            >
              Take action
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={update.isPending}
              onClick={() => setStatus("dismissed")}
            >
              Dismiss
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function RetentionSignals() {
  const { data, isLoading, isError } = useSignals();
  const signals = asArray(data);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Talent Radar"
        title="Retention signals"
        description="Early, explainable flags on flight risk — each with the evidence and reasoning behind it."
      />

      {isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-64 rounded-xl" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={AlertTriangle}
          title="Couldn't load signals"
          description="We hit a snag fetching your retention signals. Please try again shortly."
        />
      ) : signals.length === 0 ? (
        <EmptyState
          icon={Radar}
          title="All clear"
          description="No active retention signals right now. We'll surface them here as patterns emerge."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {signals.map((s) => (
            <SignalCard key={s.id} signal={s} />
          ))}
        </div>
      )}
    </div>
  );
}
