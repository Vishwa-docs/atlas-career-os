import { Check, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

/**
 * A tasteful, honest placeholder for modules that are designed and scaffolded
 * (Tier C) but not yet fully implemented. We show exactly what the module does,
 * how it fits the Career Graph, and what's wired — no fake screenshots.
 */
export function ModulePreview({
  eyebrow,
  title,
  description,
  capabilities,
  tier = "C",
}: {
  eyebrow: string;
  title: string;
  description: string;
  capabilities: string[];
  tier?: "B" | "C";
}) {
  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow={eyebrow}
        title={title}
        description={description}
        action={
          <Badge variant={tier === "B" ? "warning" : "secondary"}>
            {tier === "B" ? "In progress" : "Designed · scaffolded"}
          </Badge>
        }
      />
      <Card className="overflow-hidden">
        <div className="bg-gradient-to-br from-primary/10 via-brand/5 to-transparent p-8">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-card px-3 py-1 text-xs font-medium text-brand shadow-sm">
            <Sparkles className="h-3.5 w-3.5" /> Powered by the shared Career Graph
          </div>
          <CardContent className="grid gap-3 p-0 sm:grid-cols-2">
            {capabilities.map((c) => (
              <div key={c} className="flex items-start gap-2 rounded-lg bg-card/60 p-3 text-sm">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                <span>{c}</span>
              </div>
            ))}
          </CardContent>
        </div>
      </Card>
    </div>
  );
}
