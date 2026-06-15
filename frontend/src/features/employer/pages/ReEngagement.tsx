import { toast } from "sonner";
import { Mail, UserPlus, Users } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPercent, initials } from "@/lib/utils";
import { useReEngagement, asArray, type WarmBenchCandidate } from "../api";

function WarmCard({ candidate }: { candidate: WarmBenchCandidate }) {
  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-start gap-3">
          <Avatar className="h-11 w-11">
            <AvatarFallback>{initials(candidate.full_name)}</AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate font-semibold">{candidate.full_name}</h3>
                <p className="truncate text-sm text-muted-foreground">
                  {candidate.headline || candidate.former_role || "Former candidate"}
                </p>
              </div>
              {candidate.fit_score != null && (
                <Badge variant="brand" className="shrink-0">
                  {formatPercent(candidate.fit_score)} fit
                </Badge>
              )}
            </div>
          </div>
        </div>

        {candidate.reason && (
          <p className="rounded-lg bg-muted/60 p-3 text-sm text-foreground/90">
            {candidate.reason}
          </p>
        )}

        <GlassBoxPanel glassBox={candidate.glass_box} defaultOpen={false} />

        <Button
          size="sm"
          variant="outline"
          className="w-full"
          onClick={() => toast.success(`Outreach drafted for ${candidate.full_name}`)}
        >
          <Mail className="h-4 w-4" /> Re-engage
        </Button>
      </CardContent>
    </Card>
  );
}

export default function ReEngagement() {
  const { data, isLoading, isError } = useReEngagement();
  const candidates = asArray(data);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Talent Radar"
        title="Re-engagement"
        description="Your warm bench — strong past candidates who opted in to hear about the right new role."
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
          icon={Users}
          title="Couldn't load your warm bench"
          description="We hit a snag fetching re-engagement candidates. Please try again shortly."
        />
      ) : candidates.length === 0 ? (
        <EmptyState
          icon={UserPlus}
          title="No warm-bench candidates yet"
          description="Candidates who opt in to future opportunities after a near-miss will appear here."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {candidates.map((c) => (
            <WarmCard key={c.id} candidate={c} />
          ))}
        </div>
      )}
    </div>
  );
}
