/**
 * Small presentational table + pagination primitives shared by the admin
 * tables (Tenants, Users, Audit). Pure UI — no data fetching.
 */

import type { ReactNode } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ADMIN_PAGE_SIZE } from "../api";

export function TableShell({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">{children}</table>
      </div>
    </div>
  );
}

export function Th({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <th
      className={`whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground ${className ?? ""}`}
    >
      {children}
    </th>
  );
}

export function Td({ children, className }: { children: ReactNode; className?: string }) {
  return <td className={`px-4 py-3 align-middle ${className ?? ""}`}>{children}</td>;
}

export function TableRowSkeleton({ cols }: { cols: number }) {
  return (
    <>
      {Array.from({ length: 8 }).map((_, r) => (
        <tr key={r} className="border-t">
          {Array.from({ length: cols }).map((__, c) => (
            <td key={c} className="px-4 py-3">
              <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function Pagination({
  page,
  total,
  count,
  onPage,
  isFetching,
}: {
  page: number;
  total: number;
  count: number;
  onPage: (p: number) => void;
  isFetching?: boolean;
}) {
  const pageCount = Math.max(1, Math.ceil(total / ADMIN_PAGE_SIZE));
  const from = total === 0 ? 0 : (page - 1) * ADMIN_PAGE_SIZE + 1;
  const to = (page - 1) * ADMIN_PAGE_SIZE + count;

  return (
    <div className="flex flex-col items-center justify-between gap-3 px-1 py-3 text-sm text-muted-foreground sm:flex-row">
      <span>
        {total > 0 ? (
          <>
            Showing <span className="font-medium text-foreground">{from}</span>–
            <span className="font-medium text-foreground">{to}</span> of{" "}
            <span className="font-medium text-foreground">{total.toLocaleString()}</span>
          </>
        ) : (
          "No results"
        )}
      </span>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPage(page - 1)}
          disabled={page <= 1 || isFetching}
        >
          <ChevronLeft className="h-4 w-4" /> Prev
        </Button>
        <span className="tabular-nums">
          Page {page} / {pageCount}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPage(page + 1)}
          disabled={page >= pageCount || isFetching}
        >
          Next <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
