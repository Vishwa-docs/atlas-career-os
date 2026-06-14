import { useState } from "react";
import { Search, Users as UsersIcon } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/common";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { initials } from "@/lib/utils";
import type { Role } from "@/types/api";
import { useAdminUsers, asArray, totalOf, type AdminUser } from "../api";
import { Pagination, TableRowSkeleton, TableShell, Td, Th } from "../components/DataTable";

const ROLE_LABELS: Record<Role, string> = {
  candidate: "Candidate",
  employer_recruiter: "Recruiter",
  employer_admin: "Employer admin",
  university_staff: "University staff",
  university_admin: "University admin",
  platform_admin: "Platform admin",
};

const ROLE_VARIANT: Record<Role, "default" | "secondary" | "brand" | "success" | "warning"> = {
  candidate: "secondary",
  employer_recruiter: "default",
  employer_admin: "default",
  university_staff: "brand",
  university_admin: "brand",
  platform_admin: "warning",
};

const ROLE_FILTERS: { value: string; label: string }[] = [
  { value: "all", label: "All roles" },
  ...(Object.keys(ROLE_LABELS) as Role[]).map((r) => ({ value: r, label: ROLE_LABELS[r] })),
];

export default function Users() {
  const [page, setPage] = useState(1);
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");
  const [role, setRole] = useState("all");

  const { data, isLoading, isFetching, isError } = useAdminUsers({
    page,
    q,
    role: role === "all" ? undefined : role,
  });
  const users = asArray<AdminUser>(data);
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
        title="Users"
        description="All accounts across every tenant — search by name or email and filter by role."
      />

      <Card className="mb-6">
        <CardContent className="grid gap-4 p-4 sm:grid-cols-[minmax(0,1fr)_220px] sm:items-end">
          <form onSubmit={onSearch} className="space-y-1.5">
            <Label htmlFor="user-q">Search</Label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="user-q"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Name or email…"
                className="pl-9"
              />
            </div>
          </form>
          <div className="space-y-1.5">
            <Label>Role</Label>
            <Select
              value={role}
              onValueChange={(v) => {
                setRole(v);
                setPage(1);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="All roles" />
              </SelectTrigger>
              <SelectContent>
                {ROLE_FILTERS.map((r) => (
                  <SelectItem key={r.value} value={r.value}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {isError ? (
        <EmptyState
          icon={UsersIcon}
          title="Couldn't load users"
          description="Something went wrong fetching accounts. Please try again shortly."
        />
      ) : (
        <>
          <TableShell>
            <thead className="bg-muted/40">
              <tr>
                <Th>User</Th>
                <Th>Roles</Th>
                <Th>Organization</Th>
                <Th>Status</Th>
                <Th>Last active</Th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <TableRowSkeleton cols={5} />
              ) : users.length === 0 ? (
                <tr className="border-t">
                  <td colSpan={5}>
                    <EmptyState
                      icon={UsersIcon}
                      title={q || role !== "all" ? "No matching users" : "No users yet"}
                      description={
                        q || role !== "all" ? "Try a different search or filter." : undefined
                      }
                    />
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="border-t transition-colors hover:bg-muted/30">
                    <Td>
                      <div className="flex items-center gap-3">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback>{initials(u.full_name)}</AvatarFallback>
                        </Avatar>
                        <div className="min-w-0">
                          <div className="truncate font-medium text-foreground">{u.full_name}</div>
                          <div className="truncate text-xs text-muted-foreground">{u.email}</div>
                        </div>
                      </div>
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-1.5">
                        {(u.roles ?? []).map((r) => (
                          <Badge key={r} variant={ROLE_VARIANT[r] ?? "secondary"}>
                            {ROLE_LABELS[r] ?? r}
                          </Badge>
                        ))}
                      </div>
                    </Td>
                    <Td>{u.org_name || <span className="text-muted-foreground">—</span>}</Td>
                    <Td>
                      <Badge variant={u.status === "suspended" ? "destructive" : "outline"}>
                        {u.status ?? "active"}
                      </Badge>
                    </Td>
                    <Td className="whitespace-nowrap text-muted-foreground">
                      {u.last_active_at ? new Date(u.last_active_at).toLocaleDateString() : "—"}
                    </Td>
                  </tr>
                ))
              )}
            </tbody>
          </TableShell>
          <Pagination
            page={page}
            total={total}
            count={users.length}
            onPage={setPage}
            isFetching={isFetching}
          />
        </>
      )}
    </div>
  );
}
