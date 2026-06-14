import { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Spinner } from "@/components/common";
import { useAuth } from "@/stores/auth";
import type { Role } from "@/types/api";

/** Gate a route on authentication and (optionally) a set of allowed roles. */
export function RequireAuth({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles?: Role[];
}) {
  const { user, status, hydrate } = useAuth();
  const location = useLocation();

  useEffect(() => {
    if (status === "idle") void hydrate();
  }, [status, hydrate]);

  if (status === "idle" || status === "loading") {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner className="h-6 w-6 text-brand" />
      </div>
    );
  }

  if (status === "unauthenticated" || !user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  if (roles && !roles.some((r) => user.roles.includes(r)) && !user.roles.includes("platform_admin")) {
    return <Navigate to="/app" replace />;
  }

  return <>{children}</>;
}
