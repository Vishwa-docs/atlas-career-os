import { useState } from "react";
import {
  Baby,
  CalendarRange,
  GraduationCap,
  Heart,
  Plane,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { PageHeader, SectionHeading } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface ChapterType {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  blurb: string;
  reentry: string[];
}

const CHAPTERS: ChapterType[] = [
  {
    id: "caregiving",
    label: "Caregiving break",
    icon: Baby,
    blurb: "Stepping back to care for family. A planned pause, not a step down.",
    reentry: [
      "Keep one skill warm with a light monthly project",
      "Draft a confident 2-line narrative for the gap",
      "Re-activate your network 6–8 weeks before returning",
    ],
  },
  {
    id: "study",
    label: "Study / reskill",
    icon: GraduationCap,
    blurb: "Investing in a credential or new domain to pivot deliberately.",
    reentry: [
      "Map target roles before you start, not after",
      "Build one portfolio artefact per module",
      "Line up an internship or capstone with a hiring partner",
    ],
  },
  {
    id: "sabbatical",
    label: "Sabbatical / travel",
    icon: Plane,
    blurb: "A reset to recover energy and perspective.",
    reentry: [
      "Set a fixed return date to anchor the plan",
      "Capture transferable experiences as stories",
      "Schedule 3 reconnect coffees in your final month",
    ],
  },
  {
    id: "health",
    label: "Health recovery",
    icon: Heart,
    blurb: "Prioritising wellbeing, then returning on your own terms.",
    reentry: [
      "Consider a phased or part-time return",
      "Identify roles with flexible arrangements",
      "Frame the gap simply and move the conversation forward",
    ],
  },
];

const RAMP = [
  { phase: "Before the break", weeks: "Now", note: "Document your wins, save references, set a return intention." },
  { phase: "During", weeks: "Mid", note: "Light upskilling and occasional network touchpoints keep momentum." },
  { phase: "Re-entry runway", weeks: "−8 wks", note: "Refresh profile, reach out, and target re-entry-friendly employers." },
  { phase: "Back in motion", weeks: "Week 1", note: "Phased ramp, a 30-day plan, and a coach check-in." },
];

export default function LifeChapters() {
  const [active, setActive] = useState(CHAPTERS[0].id);
  const chapter = CHAPTERS.find((c) => c.id === active)!;

  return (
    <div className="animate-fade-in space-y-6">
      <PageHeader
        eyebrow="Life Chapters"
        title="Plan a break — and a strong return"
        description="Careers aren't linear. Plan time away with dignity, and a re-entry runway that brings you back stronger."
        action={
          <Badge variant="warning" className="gap-1">
            <Sparkles className="h-3 w-3" /> Planner
          </Badge>
        }
      />

      {/* Chapter picker */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {CHAPTERS.map((c) => {
          const Icon = c.icon;
          const isActive = c.id === active;
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => setActive(c.id)}
              className={cn(
                "rounded-xl border bg-card p-4 text-left shadow-sm transition-all hover:shadow-md",
                isActive ? "border-brand ring-2 ring-brand/30" : "hover:border-brand/40",
              )}
            >
              <Icon className={cn("h-6 w-6", isActive ? "text-brand" : "text-muted-foreground")} />
              <p className="mt-2 font-medium">{c.label}</p>
            </button>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Selected chapter detail */}
        <Card className="lg:col-span-2">
          <CardContent className="space-y-4 p-6">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-accent p-2.5">
                <chapter.icon className="h-5 w-5 text-brand" />
              </div>
              <div>
                <h2 className="font-display text-lg font-semibold">{chapter.label}</h2>
                <p className="text-sm text-muted-foreground">{chapter.blurb}</p>
              </div>
            </div>

            <div>
              <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold">
                <RotateCcw className="h-4 w-4 text-brand" /> Re-entry checklist
              </p>
              <ul className="space-y-2">
                {chapter.reentry.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand/15 text-xs font-semibold text-brand">
                      {i + 1}
                    </span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Universal ramp */}
        <Card>
          <CardContent className="p-6">
            <SectionHeading title="Your return runway" />
            <ol className="relative space-y-4 border-l-2 border-border pl-5">
              {RAMP.map((step, i) => (
                <li key={i} className="relative">
                  <span className="absolute -left-[27px] top-1 flex h-3.5 w-3.5 items-center justify-center rounded-full border-2 border-background bg-brand" />
                  <div className="flex items-center gap-2">
                    <CalendarRange className="h-3.5 w-3.5 text-muted-foreground" />
                    <p className="text-sm font-medium">{step.phase}</p>
                    <Badge variant="outline" className="ml-auto text-[10px]">
                      {step.weeks}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{step.note}</p>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
