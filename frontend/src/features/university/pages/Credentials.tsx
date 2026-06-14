import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import {
  Award,
  BadgeCheck,
  Copy,
  ScanLine,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { PageHeader, SectionHeading, Spinner } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ApiClientError } from "@/lib/apiClient";
import {
  useIssueCredential,
  useVerifyCredential,
  type IssueCredentialInput,
} from "../api";

function IssueCard() {
  const issue = useIssueCredential();
  const form = useForm<IssueCredentialInput>({
    defaultValues: {
      recipient_name: "",
      recipient_email: "",
      credential_type: "degree",
      title: "",
      program: "",
    },
  });
  const issued = issue.data;

  async function onSubmit(values: IssueCredentialInput) {
    try {
      await issue.mutateAsync(values);
      toast.success("Credential issued and anchored.");
      form.reset();
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Couldn't issue the credential.";
      toast.error(msg);
    }
  }

  function copyId(id: string) {
    void navigator.clipboard?.writeText(id);
    toast.success("Credential ID copied.");
  }

  return (
    <Card>
      <CardContent className="p-5">
        <SectionHeading
          title="Issue a credential"
          description="Sign and anchor a verifiable, tamper-evident credential."
        />
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="recipient_name">Recipient name</Label>
              <Input id="recipient_name" placeholder="Aisyah binti Rahman" {...form.register("recipient_name", { required: true })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="recipient_email">Recipient email</Label>
              <Input id="recipient_email" type="email" placeholder="aisyah@example.com" {...form.register("recipient_email")} />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="credential_type">Type</Label>
              <select
                id="credential_type"
                {...form.register("credential_type")}
                className="flex h-10 w-full items-center justify-between rounded-lg border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="degree">Degree</option>
                <option value="diploma">Diploma</option>
                <option value="micro_credential">Micro-credential</option>
                <option value="certificate">Certificate</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="program">Program</Label>
              <Input id="program" placeholder="BSc Computer Science" {...form.register("program")} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="title">Credential title</Label>
            <Input id="title" placeholder="Bachelor of Science (Hons) in Computer Science" {...form.register("title", { required: true })} />
          </div>
          <Button type="submit" variant="brand" disabled={issue.isPending}>
            {issue.isPending ? <Spinner /> : (<><Award className="h-4 w-4" /> Issue credential</>)}
          </Button>
        </form>

        {issued && (
          <div className="mt-5 rounded-xl border border-success/30 bg-success/5 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-success">
              <BadgeCheck className="h-4 w-4" /> Credential issued
            </div>
            <p className="mt-1 text-sm">{issued.title}</p>
            <p className="text-xs text-muted-foreground">Issued to {issued.recipient_name}</p>
            <div className="mt-3 flex items-center gap-2">
              <code className="truncate rounded bg-muted px-2 py-1 text-xs">{issued.id}</code>
              <Button type="button" variant="outline" size="sm" onClick={() => copyId(issued.id)}>
                <Copy className="h-3.5 w-3.5" /> Copy ID
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function VerifyCard() {
  const [id, setId] = useState("");
  const verify = useVerifyCredential();
  const result = verify.data;

  function onVerify(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = id.trim();
    if (!trimmed) return;
    verify.mutate(trimmed, {
      onError: (err) => {
        const msg = err instanceof ApiClientError ? err.message : "Couldn't verify that credential.";
        toast.error(msg);
      },
    });
  }

  const isValid = result?.valid && !result?.revoked;

  return (
    <Card>
      <CardContent className="p-5">
        <SectionHeading
          title="Verify a credential"
          description="Look up any credential ID to confirm its authenticity."
        />
        <form onSubmit={onVerify} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1 space-y-1.5">
            <Label htmlFor="verify-id">Credential ID</Label>
            <Input
              id="verify-id"
              value={id}
              onChange={(e) => setId(e.target.value)}
              placeholder="Paste a credential ID"
            />
          </div>
          <Button type="submit" variant="brand" disabled={!id.trim() || verify.isPending}>
            {verify.isPending ? <Spinner /> : (<><ScanLine className="h-4 w-4" /> Verify</>)}
          </Button>
        </form>

        {result && (
          <div className="mt-5">
            <div
              className={`flex items-center gap-2 rounded-lg p-3 text-sm font-medium ${
                isValid ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"
              }`}
            >
              {isValid ? <ShieldCheck className="h-4 w-4" /> : <ShieldAlert className="h-4 w-4" />}
              {isValid
                ? "Valid — this credential is authentic"
                : result.revoked
                  ? "Revoked — this credential is no longer valid"
                  : result.message ?? "Invalid — could not verify this credential"}
            </div>

            {result.credential && (
              <div className="mt-4 space-y-2 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">{result.credential.title}</span>
                  {result.credential.credential_type && (
                    <Badge variant="secondary">{result.credential.credential_type}</Badge>
                  )}
                </div>
                <Separator />
                <dl className="grid grid-cols-2 gap-y-2 text-xs">
                  <dt className="text-muted-foreground">Recipient</dt>
                  <dd>{result.credential.recipient_name}</dd>
                  {(result.issuer || result.credential.issuer) && (
                    <>
                      <dt className="text-muted-foreground">Issuer</dt>
                      <dd>{result.issuer ?? result.credential.issuer}</dd>
                    </>
                  )}
                  {(result.issued_on || result.credential.issued_on) && (
                    <>
                      <dt className="text-muted-foreground">Issued on</dt>
                      <dd>
                        {new Date(
                          (result.issued_on ?? result.credential.issued_on) as string,
                        ).toLocaleDateString()}
                      </dd>
                    </>
                  )}
                </dl>
              </div>
            )}

            {result.glass_box && (
              <GlassBoxPanel glassBox={result.glass_box} title="How this proof was verified" className="mt-4" defaultOpen={false} />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function Credentials() {
  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Outcomes Studio"
        title="Verifiable credentials"
        description="Issue tamper-evident credentials and verify any proof in seconds — no calls, no PDFs."
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <IssueCard />
        <VerifyCard />
      </div>
    </div>
  );
}
