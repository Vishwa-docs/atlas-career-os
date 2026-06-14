/**
 * Admin (Mission Control) data layer.
 * Local interfaces mirror docs/architecture/api-contract.md (§ Admin · Mission
 * Control). All hooks call the shared typed `api` client with stable query keys.
 */

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { GlassBox, Paginated, Role } from "@/types/api";

/* ----------------------------------------------------------------------------
 * Shared helpers
 * ------------------------------------------------------------------------- */

/** Tolerate either a Paginated<T> envelope or a bare array from the API. */
export function asArray<T>(data: Paginated<T> | T[] | undefined): T[] {
  if (!data) return [];
  return Array.isArray(data) ? data : data.items ?? [];
}

/** Read the total count from a paginated envelope (falls back to array length). */
export function totalOf<T>(data: Paginated<T> | T[] | undefined, fallback = 0): number {
  if (!data) return fallback;
  if (Array.isArray(data)) return data.length;
  return data.total ?? data.items?.length ?? fallback;
}

export const ADMIN_PAGE_SIZE = 20;

/* ----------------------------------------------------------------------------
 * Overview — GET /admin/metrics
 * ------------------------------------------------------------------------- */

export interface AdminTrendPoint {
  date: string;
  value: number;
}

export interface AdminBreakdown {
  label: string;
  value: number;
}

export interface AdminMetrics {
  total_users: number;
  active_users_30d?: number;
  total_orgs: number;
  total_jobs?: number;
  total_applications?: number;
  total_matches?: number;
  ai_calls_30d?: number;
  ai_cost_usd_30d?: number;
  new_users_trend?: AdminTrendPoint[];
  signups_by_role?: AdminBreakdown[];
  orgs_by_type?: AdminBreakdown[];
}

export function useAdminMetrics() {
  return useQuery({
    queryKey: ["admin", "metrics"],
    queryFn: () => api.get<AdminMetrics>("/admin/metrics"),
  });
}

/* ----------------------------------------------------------------------------
 * Tenants — GET /admin/tenants (paginated)
 * ------------------------------------------------------------------------- */

export interface AdminTenant {
  id: string;
  name: string;
  type?: "employer" | "university" | string;
  tier?: string;
  country?: string;
  member_count?: number;
  status?: string;
  created_at?: string;
}

export function useAdminTenants(params: { page: number; q?: string }) {
  return useQuery({
    queryKey: ["admin", "tenants", params],
    queryFn: () =>
      api.get<Paginated<AdminTenant> | AdminTenant[]>("/admin/tenants", {
        page: params.page,
        page_size: ADMIN_PAGE_SIZE,
        q: params.q || undefined,
      }),
    placeholderData: keepPreviousData,
  });
}

/* ----------------------------------------------------------------------------
 * Users — GET /admin/users (paginated)
 * ------------------------------------------------------------------------- */

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  roles: Role[];
  org_name?: string | null;
  status?: string;
  last_active_at?: string | null;
  created_at?: string;
}

export function useAdminUsers(params: { page: number; q?: string; role?: string }) {
  return useQuery({
    queryKey: ["admin", "users", params],
    queryFn: () =>
      api.get<Paginated<AdminUser> | AdminUser[]>("/admin/users", {
        page: params.page,
        page_size: ADMIN_PAGE_SIZE,
        q: params.q || undefined,
        role: params.role || undefined,
      }),
    placeholderData: keepPreviousData,
  });
}

/* ----------------------------------------------------------------------------
 * Taxonomy — GET /admin/taxonomy + browse via /taxonomy/skills|occupations
 * ------------------------------------------------------------------------- */

export interface AdminTaxonomyCounts {
  skills: number;
  occupations: number;
  transitions: number;
  skill_categories?: number;
  last_updated?: string;
}

export function useAdminTaxonomy() {
  return useQuery({
    queryKey: ["admin", "taxonomy"],
    queryFn: () => api.get<AdminTaxonomyCounts>("/admin/taxonomy"),
  });
}

export interface TaxonomySkill {
  id: string;
  name: string;
  category?: string;
}

export interface TaxonomyOccupation {
  id: string;
  title: string;
  median_salary?: number;
  currency?: string;
}

export function useTaxonomySkills(q: string) {
  return useQuery({
    queryKey: ["admin", "taxonomy", "skills", q],
    queryFn: () =>
      api.get<Paginated<TaxonomySkill> | TaxonomySkill[]>("/taxonomy/skills", {
        q: q || undefined,
        page_size: 50,
      }),
    placeholderData: keepPreviousData,
  });
}

export function useTaxonomyOccupations(q: string) {
  return useQuery({
    queryKey: ["admin", "taxonomy", "occupations", q],
    queryFn: () =>
      api.get<Paginated<TaxonomyOccupation> | TaxonomyOccupation[]>("/taxonomy/occupations", {
        q: q || undefined,
        page_size: 50,
      }),
    placeholderData: keepPreviousData,
  });
}

/* ----------------------------------------------------------------------------
 * AI Usage — GET /admin/ai-usage (the AI cost ledger)
 * ------------------------------------------------------------------------- */

export interface AiUsageByFeature {
  feature: string;
  cost_usd: number;
  calls?: number;
  tokens?: number;
}

export interface AiUsageByDay {
  date: string;
  cost_usd: number;
  tokens?: number;
  calls?: number;
}

export interface AiUsage {
  total_cost_usd: number;
  tokens: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_calls?: number;
  by_feature: AiUsageByFeature[];
  by_day: AiUsageByDay[];
  glass_box?: GlassBox;
}

export function useAiUsage() {
  return useQuery({
    queryKey: ["admin", "ai-usage"],
    queryFn: () => api.get<AiUsage>("/admin/ai-usage"),
  });
}

/* ----------------------------------------------------------------------------
 * Audit log — GET /admin/audit (paginated, filterable)
 * ------------------------------------------------------------------------- */

export interface AuditEntry {
  id: string;
  action: string;
  actor_name?: string;
  actor_email?: string;
  actor_id?: string;
  resource_type?: string;
  resource_id?: string;
  ip?: string;
  status?: string;
  at: string;
}

export function useAuditLog(params: { page: number; actor?: string; action?: string }) {
  return useQuery({
    queryKey: ["admin", "audit", params],
    queryFn: () =>
      api.get<Paginated<AuditEntry> | AuditEntry[]>("/admin/audit", {
        page: params.page,
        page_size: ADMIN_PAGE_SIZE,
        actor: params.actor || undefined,
        action: params.action || undefined,
      }),
    placeholderData: keepPreviousData,
  });
}
