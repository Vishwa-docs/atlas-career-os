import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/common";
import { useAuth } from "@/stores/auth";
import { WORKSPACE_HOME, workspaceForUser } from "@/app/nav";
import type { Role } from "@/types/api";
import { AuthLayout } from "./AuthLayout";
import { cn } from "@/lib/utils";

const schema = z
  .object({
    full_name: z.string().min(2, "Tell us your name"),
    email: z.string().email("Enter a valid email"),
    password: z.string().min(8, "At least 8 characters"),
    accountType: z.enum(["candidate", "employer", "university"]),
    org_name: z.string().optional(),
  })
  .refine((v) => v.accountType === "candidate" || !!v.org_name, {
    message: "Organization name is required",
    path: ["org_name"],
  });
type FormValues = z.infer<typeof schema>;

const ROLE_FOR_TYPE: Record<FormValues["accountType"], Role> = {
  candidate: "candidate",
  employer: "employer_admin",
  university: "university_admin",
};

const types: { value: FormValues["accountType"]; label: string; note: string }[] = [
  { value: "candidate", label: "I'm navigating my career", note: "Candidate" },
  { value: "employer", label: "I'm hiring & retaining talent", note: "Employer" },
  { value: "university", label: "I track graduate outcomes", note: "University" },
];

export default function RegisterPage() {
  const navigate = useNavigate();
  const register = useAuth((s) => s.register);
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", email: "", password: "", accountType: "candidate" },
  });
  const accountType = form.watch("accountType");

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    try {
      const user = await register({
        email: values.email,
        password: values.password,
        full_name: values.full_name,
        role: ROLE_FOR_TYPE[values.accountType],
        org_name: values.org_name,
      });
      toast.success("Account created — welcome to Atlas!");
      navigate(WORKSPACE_HOME[workspaceForUser(user)]);
    } catch {
      toast.error("Could not create the account. The email may already be in use.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout>
      <div className="mb-6">
        <h1 className="font-display text-2xl font-bold">Create your account</h1>
        <p className="text-sm text-muted-foreground">Start building your career graph.</p>
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-2">
          {types.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => form.setValue("accountType", t.value)}
              className={cn(
                "flex w-full items-center justify-between rounded-lg border p-3 text-left text-sm transition-colors",
                accountType === t.value
                  ? "border-primary bg-primary/5"
                  : "hover:bg-accent",
              )}
            >
              <span>{t.label}</span>
              <span className="text-xs text-muted-foreground">{t.note}</span>
            </button>
          ))}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="full_name">Full name</Label>
          <Input id="full_name" {...form.register("full_name")} />
          {form.formState.errors.full_name && (
            <p className="text-xs text-destructive">{form.formState.errors.full_name.message}</p>
          )}
        </div>

        {accountType !== "candidate" && (
          <div className="space-y-1.5">
            <Label htmlFor="org_name">Organization name</Label>
            <Input id="org_name" {...form.register("org_name")} />
            {form.formState.errors.org_name && (
              <p className="text-xs text-destructive">{form.formState.errors.org_name.message}</p>
            )}
          </div>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" {...form.register("email")} />
          {form.formState.errors.email && (
            <p className="text-xs text-destructive">{form.formState.errors.email.message}</p>
          )}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" {...form.register("password")} />
          {form.formState.errors.password && (
            <p className="text-xs text-destructive">{form.formState.errors.password.message}</p>
          )}
        </div>

        <Button type="submit" variant="brand" className="w-full" disabled={submitting}>
          {submitting ? <Spinner /> : "Create account"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
