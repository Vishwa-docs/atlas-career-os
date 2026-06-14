import {
  Activity,
  BadgeCheck,
  Banknote,
  BarChart3,
  Boxes,
  BriefcaseBusiness,
  Building2,
  CalendarHeart,
  CloudSun,
  Compass,
  FileText,
  GraduationCap,
  Heart,
  LayoutDashboard,
  type LucideIcon,
  Map,
  MessageCircleHeart,
  Radar,
  Recycle,
  School,
  ScrollText,
  Search,
  Shield,
  ShieldCheck,
  Sparkles,
  Users,
  Wallet,
} from "lucide-react";
import type { Role, User } from "@/types/api";

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  tier?: "A" | "B" | "C";
}

export interface NavSection {
  heading: string;
  items: NavItem[];
}

export type Workspace = "candidate" | "employer" | "university" | "admin";

export const candidateNav: NavSection[] = [
  {
    heading: "Navigate",
    items: [
      { label: "Dashboard", path: "/app", icon: LayoutDashboard, tier: "A" },
      { label: "Trajectory Atlas", path: "/app/atlas", icon: Map, tier: "A" },
      { label: "Career Copilot", path: "/app/coach", icon: Sparkles, tier: "A" },
      { label: "Career Weather", path: "/app/weather", icon: CloudSun, tier: "A" },
    ],
  },
  {
    heading: "Find work",
    items: [
      { label: "Discover jobs", path: "/app/jobs", icon: Search, tier: "A" },
      { label: "Applications", path: "/app/applications", icon: BriefcaseBusiness, tier: "A" },
      { label: "Fair Pay", path: "/app/pay", icon: Banknote, tier: "A" },
    ],
  },
  {
    heading: "Grow",
    items: [
      { label: "Profile & Résumé", path: "/app/profile", icon: FileText, tier: "A" },
      { label: "Living Portfolio", path: "/app/portfolio", icon: ScrollText, tier: "B" },
      { label: "Life Chapters", path: "/app/life-chapters", icon: CalendarHeart, tier: "B" },
      { label: "Learning Wallet", path: "/app/wallet", icon: Wallet, tier: "C" },
    ],
  },
  {
    heading: "Control",
    items: [{ label: "Data & Consent", path: "/app/consent", icon: ShieldCheck, tier: "A" }],
  },
];

export const employerNav: NavSection[] = [
  {
    heading: "Radar",
    items: [
      { label: "Dashboard", path: "/employer", icon: LayoutDashboard, tier: "A" },
      { label: "Find talent", path: "/employer/candidates", icon: Radar, tier: "A" },
      { label: "Jobs", path: "/employer/jobs", icon: BriefcaseBusiness, tier: "A" },
      { label: "Pipeline", path: "/employer/pipeline", icon: Boxes, tier: "A" },
    ],
  },
  {
    heading: "Keep & plan",
    items: [
      { label: "Retention Signals", path: "/employer/retention", icon: Heart, tier: "B" },
      { label: "Re-Engagement", path: "/employer/reengage", icon: Recycle, tier: "B" },
      { label: "Onboarding Risk", path: "/employer/onboarding", icon: Activity, tier: "B" },
      { label: "Workforce Resilience", path: "/employer/workforce", icon: BarChart3, tier: "C" },
    ],
  },
];

export const universityNav: NavSection[] = [
  {
    heading: "Outcomes Studio",
    items: [
      { label: "Dashboard", path: "/university", icon: LayoutDashboard, tier: "A" },
      { label: "Outcome Loop", path: "/university/outcomes", icon: BarChart3, tier: "A" },
      { label: "Students", path: "/university/students", icon: Users, tier: "A" },
      { label: "Readiness Profiles", path: "/university/readiness", icon: BadgeCheck, tier: "A" },
    ],
  },
  {
    heading: "Align & verify",
    items: [
      { label: "Curriculum Engine", path: "/university/curriculum", icon: GraduationCap, tier: "B" },
      { label: "Internships", path: "/university/internships", icon: Compass, tier: "B" },
      { label: "Credentials", path: "/university/credentials", icon: ScrollText, tier: "C" },
    ],
  },
];

export const adminNav: NavSection[] = [
  {
    heading: "Mission Control",
    items: [
      { label: "Overview", path: "/admin", icon: LayoutDashboard, tier: "A" },
      { label: "Tenants", path: "/admin/tenants", icon: Building2, tier: "A" },
      { label: "Users", path: "/admin/users", icon: Users, tier: "A" },
      { label: "Taxonomy", path: "/admin/taxonomy", icon: School, tier: "B" },
      { label: "AI Usage & Cost", path: "/admin/ai-usage", icon: Sparkles, tier: "A" },
      { label: "Audit Log", path: "/admin/audit", icon: Shield, tier: "A" },
    ],
  },
];

const ROLE_WORKSPACE: Record<Role, Workspace> = {
  candidate: "candidate",
  employer_recruiter: "employer",
  employer_admin: "employer",
  university_staff: "university",
  university_admin: "university",
  platform_admin: "admin",
};

export const WORKSPACE_HOME: Record<Workspace, string> = {
  candidate: "/app",
  employer: "/employer",
  university: "/university",
  admin: "/admin",
};

export const WORKSPACE_NAV: Record<Workspace, NavSection[]> = {
  candidate: candidateNav,
  employer: employerNav,
  university: universityNav,
  admin: adminNav,
};

export const WORKSPACE_LABEL: Record<Workspace, string> = {
  candidate: "Navigator",
  employer: "Talent Radar",
  university: "Outcomes Studio",
  admin: "Mission Control",
};

export const MessageIcon = MessageCircleHeart;

export function workspaceForUser(user: User): Workspace {
  // Prefer a non-candidate workspace if the user is org staff, else candidate.
  const priority: Role[] = [
    "platform_admin",
    "employer_admin",
    "employer_recruiter",
    "university_admin",
    "university_staff",
    "candidate",
  ];
  for (const role of priority) {
    if (user.roles.includes(role)) return ROLE_WORKSPACE[role];
  }
  return "candidate";
}
