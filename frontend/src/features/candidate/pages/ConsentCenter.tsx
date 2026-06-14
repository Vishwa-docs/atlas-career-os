import { useState } from "react";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import {
  Building2,
  Download,
  Eye,
  Plus,
  ShieldCheck,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import { EmptyState, PageHeader, SectionHeading, Spinner } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiClientError } from "@/lib/apiClient";
import {
  asArray,
  useAccessLog,
  useConsentGrants,
  useGrantConsent,
  useRevokeConsent,
  type AccessLogEntry,
  type ConsentGrant,
} from "../api";

const SCOPES = [
  { id: "profile", label: "Profile basics" },
  { id: "career_history", label: "Career history" },
  { id: "skills", label: "Skills" },
  { id: "salary", label: "Salary expectations" },
];

function safeDate(value?: string | null) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

export default function ConsentCenter() {
  const grants = useConsentGrants();
  const accessLog = useAccessLog();
  const grant = useGrantConsent();
  const revoke = useRevokeConsent();

  const [open, setOpen] = useState(false);
  const [orgId, setOrgId] = useState("");
  const [purpose, setPurpose] = useState("");
  const [scopes, setScopes] = useState<string[]>(["profile"]);

  const grantList = asArray<ConsentGrant>(grants.data);
  const logList = asArray<AccessLogEntry>(accessLog.data);

  function toggleScope(id: string) {
    setScopes((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  function submitGrant() {
    if (!orgId.trim() || scopes.length === 0) {
      toast.error("Enter an organization and at least one scope.");
      return;
    }
    grant.mutate(
      { grantee_org_id: orgId.trim(), scopes, purpose: purpose.trim() || undefined },
      {
        onSuccess: () => {
          toast.success("Access granted");
          setOpen(false);
          setOrgId("");
          setPurpose("");
          setScopes(["profile"]);
        },
        onError: (e) =>
          toast.error(e instanceof ApiClientError ? e.message : "Couldn't grant access."),
      },
    );
  }

  function doRevoke(id: string) {
    revoke.mutate(id, {
      onSuccess: () => toast.success("Access revoked"),
      onError: (e) =>
        toast.error(e instanceof ApiClientError ? e.message : "Couldn't revoke access."),
    });
  }

  async function exportData() {
    try {
      const data = await api.get<unknown>("/me/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "atlas-data-export.json";
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Your data export has downloaded");
    } catch (e) {
      toast.error(e instanceof ApiClientError ? e.message : "Export failed.");
    }
  }

  async function eraseData() {
    if (!window.confirm("Erase your account and all data? This cannot be undone.")) return;
    try {
      await api.delete("/me");
      toast.success("Erasure requested. You'll be signed out shortly.");
    } catch (e) {
      toast.error(e instanceof ApiClientError ? e.message : "Erasure failed.");
    }
  }

  return (
    <div className="animate-fade-in space-y-6">
      <PageHeader
        eyebrow="Data Dignity · Consent Center"
        title="You own your Career Graph"
        description="Decide exactly who can see your data, for what, and for how long. Revoke anytime."
        action={
          <Button variant="brand" onClick={() => setOpen(true)}>
            <Plus /> Grant access
          </Button>
        }
      />

      {/* Grants */}
      <div>
        <SectionHeading
          title="Active grants"
          description="Organizations you've allowed to view parts of your profile."
        />
        {grants.isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 2 }).map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-xl" />
            ))}
          </div>
        ) : grants.isError ? (
          <EmptyState icon={ShieldCheck} title="Couldn't load grants" description="Please refresh." />
        ) : grantList.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="No active grants"
            description="No organization can see your data. Grant access when you're ready to be discovered."
          />
        ) : (
          <div className="space-y-3">
            {grantList.map((g) => {
              const expires = safeDate(g.expires_at);
              return (
                <Card key={g.id}>
                  <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                    <div className="min-w-0">
                      <p className="flex items-center gap-2 font-medium">
                        <Building2 className="h-4 w-4 text-brand" />
                        {g.grantee_org_name ?? g.grantee_org_id}
                      </p>
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        {g.scopes.map((s) => (
                          <Badge key={s} variant="secondary">
                            {SCOPES.find((x) => x.id === s)?.label ?? s}
                          </Badge>
                        ))}
                      </div>
                      {g.purpose && (
                        <p className="mt-1 text-xs text-muted-foreground">Purpose: {g.purpose}</p>
                      )}
                      {expires && (
                        <p className="text-xs text-muted-foreground">
                          Expires {formatDistanceToNow(expires, { addSuffix: true })}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => doRevoke(g.id)}
                      disabled={revoke.isPending}
                    >
                      <Trash2 className="h-3.5 w-3.5" /> Revoke
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Access log */}
      <div>
        <SectionHeading title="Access log" description="Who has viewed your data, and when." />
        <Card>
          <CardContent className="p-0">
            {accessLog.isLoading ? (
              <div className="space-y-2 p-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 rounded-md" />
                ))}
              </div>
            ) : logList.length === 0 ? (
              <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
                <Eye className="h-4 w-4" /> No access recorded yet.
              </div>
            ) : (
              <ul className="divide-y">
                {logList.map((entry) => {
                  const at = safeDate(entry.at);
                  return (
                    <li key={entry.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                      <div className="min-w-0">
                        <p className="truncate">
                          <span className="font-medium">
                            {entry.actor_org_name ?? entry.actor ?? "Someone"}
                          </span>{" "}
                          <span className="text-muted-foreground">{entry.action}</span>
                          {entry.scope ? (
                            <Badge variant="outline" className="ml-2">
                              {entry.scope}
                            </Badge>
                          ) : null}
                        </p>
                      </div>
                      {at && (
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {formatDistanceToNow(at, { addSuffix: true })}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Data rights */}
      <div>
        <SectionHeading title="Your data rights" />
        <div className="grid gap-3 sm:grid-cols-2">
          <Card>
            <CardContent className="flex items-center justify-between gap-3 p-5">
              <div>
                <p className="font-medium">Export your data</p>
                <p className="text-sm text-muted-foreground">Download everything as JSON.</p>
              </div>
              <Button variant="outline" onClick={exportData}>
                <Download className="h-4 w-4" /> Export
              </Button>
            </CardContent>
          </Card>
          <Card className="border-destructive/30">
            <CardContent className="flex items-center justify-between gap-3 p-5">
              <div>
                <p className="flex items-center gap-1.5 font-medium text-destructive">
                  <TriangleAlert className="h-4 w-4" /> Erase your account
                </p>
                <p className="text-sm text-muted-foreground">Permanently delete all data.</p>
              </div>
              <Button variant="destructive" onClick={eraseData}>
                <Trash2 className="h-4 w-4" /> Erase
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Grant dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Grant access</DialogTitle>
            <DialogDescription>
              Choose what an organization can see. You can revoke at any time.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="org">Organization ID</Label>
              <Input
                id="org"
                value={orgId}
                onChange={(e) => setOrgId(e.target.value)}
                placeholder="Organization UUID"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="purpose">Purpose (optional)</Label>
              <Input
                id="purpose"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                placeholder="e.g. Recruiting for a data role"
              />
            </div>
            <div className="space-y-2">
              <Label>Scopes</Label>
              <div className="grid grid-cols-2 gap-2">
                {SCOPES.map((s) => {
                  const checked = scopes.includes(s.id);
                  return (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => toggleScope(s.id)}
                      className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                        checked
                          ? "border-brand bg-accent/50 text-foreground"
                          : "text-muted-foreground hover:border-brand/40"
                      }`}
                    >
                      {s.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)} disabled={grant.isPending}>
              Cancel
            </Button>
            <Button variant="brand" onClick={submitGrant} disabled={grant.isPending}>
              {grant.isPending ? <Spinner /> : "Grant access"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
