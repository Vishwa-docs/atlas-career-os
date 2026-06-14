import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Briefcase, MapPin, Plus, Users } from "lucide-react";
import { PageHeader, EmptyState, Spinner } from "@/components/common";
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
import { ApiClientError } from "@/lib/apiClient";
import { formatCurrency } from "@/lib/utils";
import {
  useCreateInternship,
  useInternships,
  asArray,
  type CreateInternshipInput,
  type Internship,
} from "../api";

function InternshipCard({ item }: { item: Internship }) {
  const currency = item.currency ?? "MYR";
  const stipend =
    item.stipend_min != null || item.stipend_max != null
      ? [item.stipend_min, item.stipend_max]
          .filter((v): v is number => v != null)
          .map((v) => formatCurrency(v, currency))
          .join(" – ")
      : null;
  return (
    <Card>
      <CardContent className="space-y-3 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate font-semibold">{item.title}</h3>
            <p className="truncate text-sm text-muted-foreground">
              {item.employer ?? item.org_name ?? "Host organisation"}
            </p>
          </div>
          {item.status && <Badge variant="secondary">{item.status}</Badge>}
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {item.location && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" /> {item.location}
              {item.work_mode ? ` · ${item.work_mode}` : ""}
            </span>
          )}
          {item.duration_months != null && <span>{item.duration_months} months</span>}
          {item.openings != null && (
            <span className="flex items-center gap-1">
              <Users className="h-3.5 w-3.5" /> {item.openings} openings
            </span>
          )}
        </div>
        {item.field && <Badge variant="outline">{item.field}</Badge>}
        {stipend && <p className="text-sm font-medium text-brand">{stipend} stipend</p>}
        {item.description && (
          <p className="line-clamp-3 text-sm text-muted-foreground">{item.description}</p>
        )}
      </CardContent>
    </Card>
  );
}

function CreateInternshipDialog() {
  const [open, setOpen] = useState(false);
  const create = useCreateInternship();
  const form = useForm<CreateInternshipInput>({
    defaultValues: {
      title: "",
      employer: "",
      location: "",
      work_mode: "onsite",
      field: "",
      duration_months: 3,
      openings: 1,
    },
  });

  async function onSubmit(values: CreateInternshipInput) {
    try {
      await create.mutateAsync({
        ...values,
        duration_months: values.duration_months ? Number(values.duration_months) : undefined,
        openings: values.openings ? Number(values.openings) : undefined,
        stipend_min: values.stipend_min ? Number(values.stipend_min) : undefined,
        stipend_max: values.stipend_max ? Number(values.stipend_max) : undefined,
      });
      toast.success("Internship posted to the marketplace.");
      form.reset();
      setOpen(false);
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Couldn't post the internship.";
      toast.error(msg);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="brand">
          <Plus className="h-4 w-4" /> Post internship
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Post an internship</DialogTitle>
          <DialogDescription>
            Add a placement to your marketplace. Students see it instantly in their feed.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="title">Title</Label>
            <Input id="title" placeholder="Software Engineering Intern" {...form.register("title", { required: true })} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="employer">Host organisation</Label>
              <Input id="employer" placeholder="Acme Sdn Bhd" {...form.register("employer", { required: true })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="location">Location</Label>
              <Input id="location" placeholder="Kuala Lumpur" {...form.register("location", { required: true })} />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="work_mode">Mode</Label>
              <select
                id="work_mode"
                {...form.register("work_mode")}
                className="flex h-10 w-full items-center justify-between rounded-lg border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="onsite">On-site</option>
                <option value="hybrid">Hybrid</option>
                <option value="remote">Remote</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="duration_months">Months</Label>
              <Input id="duration_months" type="number" min={1} {...form.register("duration_months")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="openings">Openings</Label>
              <Input id="openings" type="number" min={1} {...form.register("openings")} />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="stipend_min">Stipend min (MYR)</Label>
              <Input id="stipend_min" type="number" min={0} {...form.register("stipend_min")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="stipend_max">Stipend max (MYR)</Label>
              <Input id="stipend_max" type="number" min={0} {...form.register("stipend_max")} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="field">Field</Label>
            <Input id="field" placeholder="Computer Science" {...form.register("field")} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="description">Description</Label>
            <Textarea id="description" rows={3} placeholder="What the intern will work on…" {...form.register("description")} />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="brand" disabled={create.isPending}>
              {create.isPending ? <Spinner /> : "Post internship"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function Internships() {
  const { data, isLoading, isError } = useInternships();
  const internships = asArray<Internship>(data);

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Outcomes Studio"
        title="Internship marketplace"
        description="Curate and publish placements that connect your students with the right employers."
        action={<CreateInternshipDialog />}
      />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          icon={Briefcase}
          title="Couldn't load internships"
          description="Something went wrong fetching the marketplace. Please try again shortly."
        />
      ) : internships.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="No internships yet"
          description="Post your first placement to start connecting students with employers."
          action={<CreateInternshipDialog />}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {internships.map((i) => (
            <InternshipCard key={i.id} item={i} />
          ))}
        </div>
      )}
    </div>
  );
}
