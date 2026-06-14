import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import {
  Briefcase,
  MapPin,
  Plus,
  ScanLine,
  Sparkles,
  Users,
  Wand2,
} from "lucide-react";
import { PageHeader, EmptyState, Spinner } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { formatCurrency } from "@/lib/utils";
import {
  useEmployerJobs,
  useCreateJob,
  useDebiasJob,
  asArray,
  type EmployerJob,
  type DebiasResult,
} from "../api";

const createSchema = z.object({
  title: z.string().min(2, "Title is required"),
  location: z.string().min(2, "Location is required"),
  work_mode: z.string().optional(),
  seniority: z.string().optional(),
  comp_min: z.string().optional(),
  comp_max: z.string().optional(),
  skills_required: z.string().optional(),
  description: z.string().min(20, "Add a fuller description (20+ chars)"),
});
type CreateValues = z.infer<typeof createSchema>;

function CreateJobDialog() {
  const [open, setOpen] = useState(false);
  const create = useCreateJob();
  const form = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      title: "",
      location: "",
      work_mode: "hybrid",
      seniority: "mid",
      comp_min: "",
      comp_max: "",
      skills_required: "",
      description: "",
    },
  });

  async function onSubmit(values: CreateValues) {
    try {
      await create.mutateAsync({
        title: values.title,
        location: values.location,
        work_mode: values.work_mode || undefined,
        seniority: values.seniority || undefined,
        comp_min: values.comp_min ? Number(values.comp_min) : undefined,
        comp_max: values.comp_max ? Number(values.comp_max) : undefined,
        skills_required: values.skills_required
          ? values.skills_required.split(",").map((s) => s.trim()).filter(Boolean)
          : undefined,
        description: values.description,
      });
      toast.success("Role posted");
      form.reset();
      setOpen(false);
    } catch {
      toast.error("Couldn't post the role. Please try again.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="brand">
          <Plus className="h-4 w-4" /> New role
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Post a new role</DialogTitle>
          <DialogDescription>
            Add the essentials — you can run the Bias Auditor on it once it's live.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="title">Title</Label>
            <Input id="title" {...form.register("title")} placeholder="Senior Backend Engineer" />
            {form.formState.errors.title && (
              <p className="text-xs text-destructive">{form.formState.errors.title.message}</p>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="location">Location</Label>
              <Input id="location" {...form.register("location")} placeholder="Kuala Lumpur" />
              {form.formState.errors.location && (
                <p className="text-xs text-destructive">{form.formState.errors.location.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="work_mode">Work mode</Label>
              <Input id="work_mode" {...form.register("work_mode")} placeholder="hybrid" />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="seniority">Seniority</Label>
              <Input id="seniority" {...form.register("seniority")} placeholder="mid" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="comp_min">Comp min</Label>
              <Input id="comp_min" type="number" {...form.register("comp_min")} placeholder="8000" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="comp_max">Comp max</Label>
              <Input id="comp_max" type="number" {...form.register("comp_max")} placeholder="12000" />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="skills_required">Skills required (comma-separated)</Label>
            <Input
              id="skills_required"
              {...form.register("skills_required")}
              placeholder="Go, PostgreSQL, Kafka"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              rows={5}
              {...form.register("description")}
              placeholder="What the role does, the team, and what success looks like…"
            />
            {form.formState.errors.description && (
              <p className="text-xs text-destructive">{form.formState.errors.description.message}</p>
            )}
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="brand" disabled={create.isPending}>
              {create.isPending ? <Spinner /> : "Post role"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function DebiasSection({ jobId }: { jobId: string }) {
  const debias = useDebiasJob();
  const [result, setResult] = useState<DebiasResult | null>(null);

  async function run() {
    try {
      const r = await debias.mutateAsync(jobId);
      setResult(r);
      toast.success(
        r.issues.length === 0
          ? "No bias issues found — nice."
          : `Found ${r.issues.length} issue${r.issues.length === 1 ? "" : "s"} to consider`,
      );
    } catch {
      toast.error("Couldn't run the Bias Auditor.");
    }
  }

  return (
    <div className="border-t pt-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-sm font-medium">
          <ScanLine className="h-4 w-4 text-brand" /> Bias Auditor
        </p>
        <Button size="sm" variant="outline" onClick={run} disabled={debias.isPending}>
          {debias.isPending ? <Spinner /> : <Wand2 className="h-4 w-4" />}
          De-bias JD
        </Button>
      </div>

      {result && (
        <div className="mt-3 space-y-4">
          {result.issues.length === 0 ? (
            <p className="rounded-lg bg-success/10 p-3 text-sm text-success">
              No biased or exclusionary language detected.
            </p>
          ) : (
            <ul className="space-y-2">
              {result.issues.map((issue, i) => (
                <li key={i} className="rounded-lg border p-3 text-sm">
                  <p className="font-medium text-destructive">“{issue.phrase}”</p>
                  <p className="mt-0.5 text-muted-foreground">{issue.why}</p>
                  <p className="mt-1">
                    <span className="font-medium text-success">Suggest:</span> {issue.suggestion}
                  </p>
                </li>
              ))}
            </ul>
          )}

          {result.rewritten && (
            <div>
              <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <Sparkles className="h-3.5 w-3.5 text-brand" /> Suggested rewrite
              </p>
              <div className="whitespace-pre-wrap rounded-lg bg-muted/60 p-3 text-sm leading-relaxed">
                {result.rewritten}
              </div>
            </div>
          )}

          <GlassBoxPanel glassBox={result.glass_box} defaultOpen={false} />
        </div>
      )}
    </div>
  );
}

function JobCard({ job }: { job: EmployerJob }) {
  const comp =
    job.comp_min != null && job.comp_max != null
      ? `${formatCurrency(job.comp_min, job.currency)} – ${formatCurrency(job.comp_max, job.currency)}`
      : null;

  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-semibold">{job.title}</h3>
            <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" /> {job.location}
              </span>
              {job.work_mode && <span className="capitalize">{job.work_mode}</span>}
              {job.seniority && <span className="capitalize">{job.seniority}</span>}
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            {job.status && <Badge variant="secondary">{job.status}</Badge>}
            {job.applicant_count != null && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Users className="h-3.5 w-3.5" /> {job.applicant_count}
              </span>
            )}
          </div>
        </div>

        {comp && <p className="text-sm font-medium">{comp}</p>}

        {job.skills_required && job.skills_required.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {job.skills_required.slice(0, 8).map((s) => (
              <Badge key={s} variant="outline">
                {s}
              </Badge>
            ))}
          </div>
        )}

        <DebiasSection jobId={job.id} />
      </CardContent>
    </Card>
  );
}

export default function Jobs() {
  const { data, isLoading, isError } = useEmployerJobs();
  const jobs = asArray(data);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Talent Radar"
        title="Roles"
        description="Post and manage your open roles, and keep job descriptions inclusive with the Bias Auditor."
        action={<CreateJobDialog />}
      />

      {isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-56 rounded-xl" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={Briefcase}
          title="Couldn't load your roles"
          description="We hit a snag fetching your job listings. Please try again shortly."
        />
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="No roles posted yet"
          description="Post your first role to start matching with consenting candidates."
          action={<CreateJobDialog />}
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {jobs.map((j) => (
            <JobCard key={j.id} job={j} />
          ))}
        </div>
      )}
    </div>
  );
}
