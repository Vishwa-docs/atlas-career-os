import { useState } from "react";
import { ScrollText, Search } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/common";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuditLog, asArray, totalOf, type AuditEntry } from "../api";
import { Pagination, TableRowSkeleton, TableShell, Td, Th } from "../components/DataTable";

function actionVariant(action: string): "default" | "secondary" | "success" | "warning" | "destructive" {
  const a = action.toLowerCase();
  if (a.includes("delete") || a.includes("revoke") || a.includes("suspend") || a.includes("fail"))
    return "destructive";
  if (a.includes("create") || a.includes("grant") || a.includes("login")) return "success";
  if (a.includes("update") || a.includes("patch") || a.includes("export")) return "warning";
  return "secondary";
}

export default function Audit() {
  const [page, setPage] = useState(1);
  const [actorDraft, setActorDraft] = useState("");
  const [actionDraft, setActionDraft] = useState("");
  const [filters, setFilters] = useState<{ actor?: string; action?: string }>({});

  const { data, isLoading, isFetching, isError } = useAuditLog({ page, ...filters });
  const entries = asArray<AuditEntry>(data);
  const total = totalOf(data);

  function onApply(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setFilters({ actor: actorDraft.trim() || undefined, action: actionDraft.trim() || undefined });
  }

  function onClear() {
    setActorDraft("");
    setActionDraft("");
    setPage(1);
    setFilters({});
  }

  const hasFilters = !!filters.actor || !!filters.action;

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Mission Control"
        title="Audit log"
        description="An immutable record of who did what, to which resource, and when — across the platform."
      />

      <Card className="mb-6">
        <CardContent className="p-4">
          <form
            onSubmit={onApply}
            className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end"
          >
            <div className="space-y-1.5">
              <Label htmlFor="actor">Actor</Label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="actor"
                  value={actorDraft}
                  onChange={(e) => setActorDraft(e.target.value)}
                  placeholder="Name, email or ID…"
                  className="pl-9"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="action">Action</Label>
              <Input
                id="action"
                value={actionDraft}
                onChange={(e) => setActionDraft(e.target.value)}
                placeholder="e.g. user.login, job.create"
              />
            </div>
            <div className="flex gap-2">
              <Button type="submit" variant="brand">
                Filter
              </Button>
              {hasFilters && (
                <Button type="button" variant="outline" onClick={onClear}>
                  Clear
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {isError ? (
        <EmptyState
          icon={ScrollText}
          title="Couldn't load the audit log"
          description="Something went wrong fetching audit entries. Please try again shortly."
        />
      ) : (
        <>
          <TableShell>
            <thead className="bg-muted/40">
              <tr>
                <Th>Time</Th>
                <Th>Actor</Th>
                <Th>Action</Th>
                <Th>Resource</Th>
                <Th>Source</Th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <TableRowSkeleton cols={5} />
              ) : entries.length === 0 ? (
                <tr className="border-t">
                  <td colSpan={5}>
                    <EmptyState
                      icon={ScrollText}
                      title={hasFilters ? "No matching events" : "No audit events yet"}
                      description={hasFilters ? "Try broadening your filters." : undefined}
                    />
                  </td>
                </tr>
              ) : (
                entries.map((e) => (
                  <tr key={e.id} className="border-t transition-colors hover:bg-muted/30">
                    <Td className="whitespace-nowrap text-muted-foreground">
                      {new Date(e.at).toLocaleString()}
                    </Td>
                    <Td>
                      <div className="font-medium text-foreground">
                        {e.actor_name || e.actor_email || e.actor_id || "System"}
                      </div>
                      {e.actor_name && e.actor_email && (
                        <div className="text-xs text-muted-foreground">{e.actor_email}</div>
                      )}
                    </Td>
                    <Td>
                      <Badge variant={actionVariant(e.action)} className="font-mono text-[11px]">
                        {e.action}
                      </Badge>
                    </Td>
                    <Td>
                      {e.resource_type ? (
                        <span>
                          <span className="text-foreground">{e.resource_type}</span>
                          {e.resource_id && (
                            <span className="ml-1 font-mono text-xs text-muted-foreground">
                              {e.resource_id.slice(0, 8)}
                            </span>
                          )}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </Td>
                    <Td className="whitespace-nowrap font-mono text-xs text-muted-foreground">
                      {e.ip || "—"}
                    </Td>
                  </tr>
                ))
              )}
            </tbody>
          </TableShell>
          <Pagination
            page={page}
            total={total}
            count={entries.length}
            onPage={setPage}
            isFetching={isFetching}
          />
        </>
      )}
    </div>
  );
}
