import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Award, Briefcase, NotebookPen, Plus, Sparkles } from "lucide-react";
import { EmptyState, PageHeader, SectionHeading, Spinner } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useProfile, type CareerEvent } from "../api";

interface JournalEntry {
  id: string;
  text: string;
  at: string;
}

function fmtDate(value?: string) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

export default function LivingPortfolio() {
  const profile = useProfile();
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [draft, setDraft] = useState("");

  const events = useMemo<CareerEvent[]>(() => {
    const list = profile.data?.career_events ?? [];
    return [...list].sort((a, b) => (b.start_date ?? "").localeCompare(a.start_date ?? ""));
  }, [profile.data]);

  function addEntry() {
    const text = draft.trim();
    if (!text) return;
    setJournal((j) => [
      { id: crypto.randomUUID(), text, at: new Date().toISOString() },
      ...j,
    ]);
    setDraft("");
    toast.success("Journal entry added");
  }

  return (
    <div className="animate-fade-in space-y-6">
      <PageHeader
        eyebrow="Living Portfolio"
        title="Your story, always current"
        description="A growing record of your roles and wins. Capture progress as it happens — not just at review time."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Timeline */}
        <div className="lg:col-span-2">
          <SectionHeading title="Career timeline" />
          {profile.isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-20 rounded-xl" />
              ))}
            </div>
          ) : events.length === 0 ? (
            <EmptyState
              icon={Briefcase}
              title="No roles on your timeline yet"
              description="Add roles in your Profile Builder and they'll appear here."
            />
          ) : (
            <ol className="relative space-y-5 border-l-2 border-border pl-6">
              {events.map((ev) => (
                <li key={ev.id} className="relative">
                  <span className="absolute -left-[31px] top-1.5 flex h-4 w-4 items-center justify-center rounded-full border-2 border-background bg-brand" />
                  <Card>
                    <CardContent className="p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-semibold">{ev.title || "Untitled role"}</p>
                        <Badge variant="outline">
                          {fmtDate(ev.start_date)}
                          {ev.start_date ? " — " : ""}
                          {ev.end_date ? fmtDate(ev.end_date) : ev.start_date ? "Present" : ""}
                        </Badge>
                      </div>
                      {ev.organization && (
                        <p className="text-sm text-muted-foreground">{ev.organization}</p>
                      )}
                      {ev.description && (
                        <p className="mt-2 text-sm text-foreground/80">{ev.description}</p>
                      )}
                    </CardContent>
                  </Card>
                </li>
              ))}
            </ol>
          )}
        </div>

        {/* Work journal */}
        <div className="space-y-4">
          <SectionHeading title="Work journal" description="Jot a win, lesson, or milestone." />
          <Card>
            <CardContent className="space-y-3 p-4">
              <Textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={3}
                placeholder="Shipped the onboarding redesign — cut drop-off by 18%…"
              />
              <Button variant="brand" className="w-full" onClick={addEntry} disabled={!draft.trim()}>
                {profile.isLoading ? <Spinner /> : <Plus />} Add entry
              </Button>
            </CardContent>
          </Card>

          <div className="space-y-3">
            {journal.length === 0 ? (
              <div className="flex items-center gap-2 rounded-xl border border-dashed p-4 text-sm text-muted-foreground">
                <NotebookPen className="h-4 w-4 text-brand" />
                Your entries will appear here and can seed your portfolio.
              </div>
            ) : (
              journal.map((j) => (
                <Card key={j.id}>
                  <CardContent className="p-4">
                    <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Sparkles className="h-3 w-3 text-brand" />
                      {new Date(j.at).toLocaleString(undefined, {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </p>
                    <p className="mt-1 text-sm">{j.text}</p>
                  </CardContent>
                </Card>
              ))
            )}
          </div>

          <div className="flex items-start gap-2 rounded-xl border border-primary/20 bg-accent/40 p-3 text-xs text-muted-foreground">
            <Award className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
            Journal entries stay on this device for now. Saving to your Career Graph is coming soon.
          </div>
        </div>
      </div>
    </div>
  );
}
