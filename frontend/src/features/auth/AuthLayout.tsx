import { Link } from "react-router-dom";
import { Compass, Eye, ShieldCheck } from "lucide-react";
import { AtlasWordmark } from "@/components/logo";

/** Two-pane auth layout: brand story on the left, form on the right. */
export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-primary to-brand p-12 text-primary-foreground lg:flex">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(50%_50%_at_30%_20%,rgba(255,255,255,0.18),transparent)]" />
        <Link to="/" className="relative">
          <AtlasWordmark className="[&_*]:text-primary-foreground" />
        </Link>
        <div className="relative space-y-6">
          <h2 className="font-display text-3xl font-bold leading-tight">
            A map for a 40-year career — not a fortune-teller.
          </h2>
          <ul className="space-y-3 text-primary-foreground/90">
            <li className="flex items-center gap-3"><Compass className="h-5 w-5" /> See realistic next moves with ranges</li>
            <li className="flex items-center gap-3"><Eye className="h-5 w-5" /> Every recommendation explained</li>
            <li className="flex items-center gap-3"><ShieldCheck className="h-5 w-5" /> You own your career graph</li>
          </ul>
        </div>
        <p className="relative text-sm text-primary-foreground/70">
          Talentbank Tech Hackathon · First Cohort 2026
        </p>
      </div>
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">{children}</div>
      </div>
    </div>
  );
}
