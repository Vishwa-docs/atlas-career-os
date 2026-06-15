import { HeartPulse, ShieldAlert } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPercent, initials } from "@/lib/utils";
import { useOnboardingRisk, asArray, type OnboardingRiskItem } from "../api";

const RISK_BADGE: Record<string, "destructive" | "warning" | "success"> = {
  high: "destructive",
  medium: "warning",
  low: "success",
};

function RiskCard({ item }: { item: OnboardingRiskItem }) {
  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-start gap-3">
          <Avatar className="h-11 w-11">
            <AvatarFallback>{initials(item.full_name)}</AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate font-semibold">{item.full_name}</h3>
                {(item.role || item.headline) && (
                  <p className="truncate text-sm text-muted-foreground">
                    {item.role || item.headline}
                  </p>
                )}
              </div>
              {item.risk_level && (
                <Badge variant={RISK_BADGE[item.risk_level] ?? "secondary"} className="shrink-0 capitalize">
                  {item.risk_level} risk
                </Badge>
              )}
            </div>
          </div>
        </div>

        {item.risk_score != null && (
          <div>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Risk score</span>
              <span className="font-medium tabular-nums">{formatPercent(item.risk_score)}</span>
            </div>
            <Progress value={item.risk_score * 100} className="h-1.5" />
          </div>
        )}

        <GlassBoxPanel glassBox={item.glass_box} defaultOpen={false} />
      </CardContent>
    </Card>
  );
}

export default function OnboardingRisk() {
  const { data, isLoading, isError } = useOnboardingRisk();
  const items = asArray(data);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Talent Radar"
        title="Onboarding risk"
        description="First-60-day health for new hires, with the signals driving each risk read."
        action={<Badge variant="warning">In progress</Badge>}
      />

      {isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-56 rounded-xl" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={ShieldAlert}
          title="Couldn't load onboarding risk"
          description="We hit a snag fetching new-hire risk. Please try again shortly."
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon={HeartPulse}
          title="No new hires at risk"
          description="New hires in their first 60 days will appear here with a risk read."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {items.map((i) => (
            <RiskCard key={i.id} item={i} />
          ))}
        </div>
      )}
    </div>
  );
}
