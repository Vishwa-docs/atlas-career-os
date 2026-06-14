import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Building2, GraduationCap, Shield, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/common";
import { useAuth } from "@/stores/auth";
import { WORKSPACE_HOME, workspaceForUser } from "@/app/nav";
import { AuthLayout } from "./AuthLayout";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormValues = z.infer<typeof schema>;

const demoAccounts = [
  { label: "Candidate", email: "aisyah@demo.atlas", icon: UserRound },
  { label: "Employer", email: "daniel@demo.atlas", icon: Building2 },
  { label: "University", email: "dr.tan@demo.atlas", icon: GraduationCap },
  { label: "Admin", email: "admin@demo.atlas", icon: Shield },
];
const DEMO_PASSWORD = "demo1234";

export default function LoginPage() {
  const navigate = useNavigate();
  const login = useAuth((s) => s.login);
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    try {
      const user = await login(values.email, values.password);
      toast.success(`Welcome back, ${user.full_name.split(" ")[0]}`);
      navigate(WORKSPACE_HOME[workspaceForUser(user)]);
    } catch {
      toast.error("Invalid email or password.");
    } finally {
      setSubmitting(false);
    }
  }

  async function quickLogin(email: string) {
    form.setValue("email", email);
    form.setValue("password", DEMO_PASSWORD);
    await onSubmit({ email, password: DEMO_PASSWORD });
  }

  return (
    <AuthLayout>
      <div className="mb-8">
        <h1 className="font-display text-2xl font-bold">Welcome back</h1>
        <p className="text-sm text-muted-foreground">Sign in to continue navigating.</p>
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" placeholder="you@example.com" {...form.register("email")} />
          {form.formState.errors.email && (
            <p className="text-xs text-destructive">{form.formState.errors.email.message}</p>
          )}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" placeholder="••••••••" {...form.register("password")} />
          {form.formState.errors.password && (
            <p className="text-xs text-destructive">{form.formState.errors.password.message}</p>
          )}
        </div>
        <Button type="submit" variant="brand" className="w-full" disabled={submitting}>
          {submitting ? <Spinner /> : "Sign in"}
        </Button>
      </form>

      <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
        <div className="h-px flex-1 bg-border" /> or try a demo account <div className="h-px flex-1 bg-border" />
      </div>

      <div className="grid grid-cols-2 gap-2">
        {demoAccounts.map((a) => (
          <Button
            key={a.email}
            variant="outline"
            size="sm"
            disabled={submitting}
            onClick={() => quickLogin(a.email)}
          >
            <a.icon className="h-4 w-4" /> {a.label}
          </Button>
        ))}
      </div>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        New here?{" "}
        <Link to="/register" className="font-medium text-primary hover:underline">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  );
}
