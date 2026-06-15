import { Suspense, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { HelpCircle, LogOut, Moon, Sun } from "lucide-react";
import { AtlasWordmark } from "@/components/logo";
import { GuidedTour } from "@/components/guided-tour";
import { TOUR_STEPS } from "./tourSteps";
import { Spinner } from "@/components/common";
import {
  Avatar,
  AvatarFallback,
} from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ErrorBoundary } from "@/components/error-boundary";
import { cn, initials } from "@/lib/utils";
import { useAuth } from "@/stores/auth";
import { NotificationBell } from "@/features/notifications/NotificationBell";
import { useNotificationsRealtime } from "@/features/notifications/api";
import { useTheme } from "./theme";
import { WORKSPACE_LABEL, WORKSPACE_NAV, workspaceForUser } from "./nav";

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggle } = useTheme();
  const [tourOpen, setTourOpen] = useState(false);
  useNotificationsRealtime();

  if (!user) return null;
  const workspace = workspaceForUser(user);
  const sections = WORKSPACE_NAV[workspace];

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r bg-card/50 lg:flex">
        <div className="flex h-16 items-center border-b px-5">
          <Link to="/">
            <AtlasWordmark />
          </Link>
        </div>
        <div className="px-5 py-3">
          <Badge variant="brand" className="gap-1.5">
            {WORKSPACE_LABEL[workspace]}
          </Badge>
        </div>
        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-2">
          {sections.map((section) => (
            <div key={section.heading}>
              <p className="px-3 pb-1.5 text-[0.65rem] font-semibold uppercase tracking-widest text-muted-foreground">
                {section.heading}
              </p>
              <ul className="space-y-0.5">
                {section.items.map((item) => (
                  <li key={item.path}>
                    <NavLink
                      to={item.path}
                      end={item.path.split("/").length <= 2}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                          isActive
                            ? "bg-primary/10 text-primary"
                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                        )
                      }
                    >
                      <item.icon className="h-4 w-4" />
                      <span className="flex-1">{item.label}</span>
                      {item.tier && item.tier !== "A" && (
                        <span className="text-[0.6rem] font-semibold text-muted-foreground/60">
                          {item.tier}
                        </span>
                      )}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </aside>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background/80 px-5 backdrop-blur-xl">
          <div className="lg:hidden">
            <AtlasWordmark />
          </div>
          <div className="hidden text-sm text-muted-foreground lg:block">
            Welcome back, <span className="font-medium text-foreground">{user.full_name.split(" ")[0]}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setTourOpen(true)}
              className="gap-1.5"
            >
              <HelpCircle className="h-4 w-4" />
              <span className="hidden sm:inline">Take a tour</span>
            </Button>
            <NotificationBell />
            <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme">
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <Avatar className="h-9 w-9">
                    <AvatarFallback>{initials(user.full_name)}</AvatarFallback>
                  </Avatar>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="font-medium">{user.full_name}</div>
                  <div className="text-xs font-normal text-muted-foreground">{user.email}</div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={async () => {
                    await logout();
                    navigate("/login");
                  }}
                >
                  <LogOut className="h-4 w-4" /> Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main className="flex-1 px-5 py-6 sm:px-8 sm:py-8">
          <div className="mx-auto max-w-7xl">
            <ErrorBoundary resetKey={location.pathname}>
              <Suspense
                fallback={
                  <div className="flex h-64 items-center justify-center">
                    <Spinner className="h-6 w-6 text-brand" />
                  </div>
                }
              >
                <Outlet />
              </Suspense>
            </ErrorBoundary>
          </div>
        </main>
      </div>

      <GuidedTour
        steps={TOUR_STEPS[workspace]}
        open={tourOpen}
        onClose={() => setTourOpen(false)}
      />
    </div>
  );
}
