import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Users } from "lucide-react";
import { PageHeader, EmptyState, Spinner } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPercent, initials } from "@/lib/utils";
import { useStudents, asArray, type UniversityStudent } from "../api";

function readinessTone(score: number): "success" | "warning" | "default" {
  if (score >= 0.7) return "success";
  if (score >= 0.4) return "warning";
  return "default";
}

function ReadinessCell({ score }: { score: number }) {
  const tone = readinessTone(score);
  const text =
    tone === "success" ? "text-success" : tone === "warning" ? "text-warning-foreground" : "text-muted-foreground";
  return (
    <div className="flex items-center gap-2">
      <Progress value={score * 100} className="h-1.5 w-24" />
      <span className={`text-xs font-medium tabular-nums ${text}`}>{formatPercent(score)}</span>
    </div>
  );
}

export default function Students() {
  const [draftQ, setDraftQ] = useState("");
  const [q, setQ] = useState("");
  const [program, setProgram] = useState("");

  const { data, isLoading, isFetching, isError } = useStudents();
  const allStudents = useMemo(() => asArray<UniversityStudent>(data), [data]);

  const programs = useMemo(() => {
    const set = new Set<string>();
    for (const s of allStudents) if (s.program) set.add(s.program);
    return Array.from(set).sort();
  }, [allStudents]);

  // The backend roster endpoint takes no query params, so filter client-side.
  const students = useMemo(() => {
    const needle = q.toLowerCase();
    return allStudents.filter((s) => {
      if (program && s.program !== program) return false;
      if (!needle) return true;
      return [s.full_name, s.program, s.field]
        .some((v) => v?.toLowerCase().includes(needle));
    });
  }, [allStudents, q, program]);

  function onSearch(e: React.FormEvent) {
    e.preventDefault();
    setQ(draftQ.trim());
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Outcomes Studio"
        title="Student roster"
        description="Every student with a live readiness score — search, filter and drill into their Adaptive Readiness Profile."
      />

      <Card className="mb-6">
        <CardContent className="p-5">
          <form onSubmit={onSearch} className="grid gap-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto] sm:items-end">
            <div className="space-y-1.5">
              <Label htmlFor="q">Search students</Label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="q"
                  value={draftQ}
                  onChange={(e) => setDraftQ(e.target.value)}
                  placeholder="Name, program or field"
                  className="pl-9"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="program">Program</Label>
              <select
                id="program"
                value={program}
                onChange={(e) => setProgram(e.target.value)}
                className="flex h-10 w-full items-center justify-between rounded-lg border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">All programs</option>
                {programs.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <Button type="submit" variant="brand">
              <Search className="h-4 w-4" /> Search
            </Button>
          </form>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={Users}
          title="Couldn't load students"
          description="Something went wrong fetching the roster. Please try again shortly."
        />
      ) : students.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No students found"
          description="No students match your filters yet. Try a broader search or clear the program filter."
        />
      ) : (
        <Card className="overflow-hidden">
          {isFetching && (
            <div className="flex items-center gap-2 border-b px-5 py-2 text-xs text-muted-foreground">
              <Spinner /> Refreshing roster…
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-5 py-3 font-medium">Student</th>
                  <th className="px-5 py-3 font-medium">Program</th>
                  <th className="px-5 py-3 font-medium">Year</th>
                  <th className="px-5 py-3 font-medium">Readiness</th>
                  <th className="px-5 py-3 font-medium text-right">Profile</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {students.map((s) => (
                  <tr key={s.id} className="hover:bg-muted/30">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback className="text-xs">{initials(s.full_name)}</AvatarFallback>
                        </Avatar>
                        <div className="min-w-0">
                          <p className="truncate font-medium">{s.full_name}</p>
                          {s.field && <p className="truncate text-xs text-muted-foreground">{s.field}</p>}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-muted-foreground">{s.program ?? "—"}</td>
                    <td className="px-5 py-3">
                      {s.year != null ? <Badge variant="secondary">{s.year}</Badge> : "—"}
                    </td>
                    <td className="px-5 py-3">
                      {s.readiness_score != null ? (
                        <ReadinessCell score={s.readiness_score} />
                      ) : (
                        <span className="text-xs text-muted-foreground">Not assessed</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Button asChild variant="outline" size="sm">
                        <Link to={`/university/readiness?student=${s.id}`}>View</Link>
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
