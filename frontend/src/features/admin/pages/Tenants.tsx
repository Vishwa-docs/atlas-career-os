import { useState } from "react";
import { Building2, GraduationCap, Search } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/common";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useAdminTenants, asArray, totalOf, type AdminTenant } from "../api";
import { Pagination, TableRowSkeleton, TableShell, Td, Th } from "../components/DataTable";

function TypeBadge({ type }: { type?: string }) {
  if (type === "university") {
    return (
      <Badge variant="brand" className="gap-1">
        <GraduationCap className="h-3 w-3" /> University
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="gap-1">
      <Building2 className="h-3 w-3" /> Employer
    </Badge>
  );
}

function TierBadge({ tier }: { tier?: string }) {
  if (!tier) return <span className="text-muted-foreground">—</span>;
  const variant =
    tier.toLowerCase() === "enterprise"
      ? "success"
      : tier.toLowerCase() === "free"
        ? "outline"
        : "default";
  return <Badge variant={variant}>{tier}</Badge>;
}

export default function Tenants() {
  const [page, setPage] = useState(1);
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");

  const { data, isLoading, isFetching, isError } = useAdminTenants({ page, q });
  const tenants = asArray<AdminTenant>(data);
  const total = totalOf(data);

  function onSearch(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setQ(draft.trim());
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Mission Control"
        title="Tenants"
        description="Every organization on Atlas — employers and universities, their tier and home country."
      />

      <Card className="mb-6">
        <CardContent className="p-4">
          <form onSubmit={onSearch} className="relative max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Search organizations…"
              className="pl-9"
            />
          </form>
        </CardContent>
      </Card>

      {isError ? (
        <EmptyState
          icon={Building2}
          title="Couldn't load tenants"
          description="Something went wrong fetching organizations. Please try again shortly."
        />
      ) : (
        <>
          <TableShell>
            <thead className="bg-muted/40">
              <tr>
                <Th>Organization</Th>
                <Th>Type</Th>
                <Th>Tier</Th>
                <Th>Country</Th>
                <Th className="text-right">Members</Th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <TableRowSkeleton cols={5} />
              ) : tenants.length === 0 ? (
                <tr className="border-t">
                  <td colSpan={5}>
                    <EmptyState
                      icon={Building2}
                      title={q ? "No matching organizations" : "No tenants yet"}
                      description={q ? "Try a different search term." : undefined}
                    />
                  </td>
                </tr>
              ) : (
                tenants.map((t) => (
                  <tr key={t.id} className="border-t transition-colors hover:bg-muted/30">
                    <Td>
                      <div className="font-medium text-foreground">{t.name}</div>
                      {t.status && (
                        <div className="text-xs text-muted-foreground">{t.status}</div>
                      )}
                    </Td>
                    <Td>
                      <TypeBadge type={t.type} />
                    </Td>
                    <Td>
                      <TierBadge tier={t.tier} />
                    </Td>
                    <Td>{t.country || <span className="text-muted-foreground">—</span>}</Td>
                    <Td className="text-right tabular-nums">{t.member_count ?? "—"}</Td>
                  </tr>
                ))
              )}
            </tbody>
          </TableShell>
          <Pagination
            page={page}
            total={total}
            count={tenants.length}
            onPage={setPage}
            isFetching={isFetching}
          />
        </>
      )}
    </div>
  );
}
