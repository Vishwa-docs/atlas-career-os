/**
 * Candidate (Navigator) data layer.
 * Local interfaces mirror docs/architecture/api-contract.md. All hooks call the
 * shared typed `api` client and use stable query keys for cache coherence.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { GlassBox, Paginated } from "@/types/api";

/* ----------------------------------------------------------------------------
 * Shared shapes
 * ------------------------------------------------------------------------- */

export interface SalaryRange {
  min: number;
  max: number;
  median?: number;
  currency: string;
}

export interface SkillGap {
  skill: string;
  have: number;
  need: number;
}

/* ----------------------------------------------------------------------------
 * Dashboard
 * ------------------------------------------------------------------------- */

export interface DashboardStat {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "default" | "brand" | "success" | "warning";
}

export interface RecentMatch {
  job_id: string;
  title: string;
  company: string;
  location?: string;
  score: number;
}

export interface CoachNudge {
  id: string;
  title: string;
  body: string;
  cta_label?: string;
  cta_to?: string;
  tone?: "info" | "success" | "warning";
}

export interface MarketSnapshot {
  outlook?: "sunny" | "cloudy" | "stormy";
  demand_index?: number;
  salary_drift_pct?: number;
  summary?: string;
  rising_skills?: string[];
}

export interface CandidateDashboard {
  stats: DashboardStat[];
  recent_matches: RecentMatch[];
  nudges: CoachNudge[];
  market_snapshot: MarketSnapshot | null;
  completeness?: number;
}

/**
 * Aggregate counters the backend may surface as an object instead of a
 * pre-built tile array. Mirrors the alternate `stats` object shape:
 * `{applications, matches, profile_completeness, market_percentile}`.
 */
interface DashboardStatsObject {
  applications?: number;
  matches?: number;
  profile_completeness?: number;
  market_percentile?: number | null;
}

/** Exactly what `GET /candidates/me/dashboard` puts on the wire. */
interface CandidateDashboardWire {
  stats: DashboardStat[] | DashboardStatsObject;
  recent_matches?: RecentMatch[];
  nudges?: CoachNudge[];
  market_snapshot?: MarketSnapshot | null;
  completeness?: number;
}

/** Turn the `stats` object form into the StatCard array the UI renders. */
function statsObjectToTiles(s: DashboardStatsObject): DashboardStat[] {
  return [
    { label: "Applications", value: s.applications ?? 0, tone: "brand" },
    {
      label: "Matches",
      value: s.matches ?? 0,
      hint: "Roles aligned to your trajectory",
    },
    {
      label: "Profile complete",
      value: `${Math.round(s.profile_completeness ?? 0)}%`,
      tone: (s.profile_completeness ?? 0) >= 80 ? "success" : "warning",
    },
    {
      label: "Market percentile",
      value: s.market_percentile != null ? `${Math.round(s.market_percentile)}%` : "—",
      hint: s.market_percentile != null ? undefined : "Set a target occupation",
    },
  ];
}

/** Normalise the wire payload into the shape the dashboard component consumes. */
function normalizeDashboard(raw: CandidateDashboardWire): CandidateDashboard {
  const stats = Array.isArray(raw.stats) ? raw.stats : statsObjectToTiles(raw.stats);
  return {
    stats,
    recent_matches: raw.recent_matches ?? [],
    nudges: raw.nudges ?? [],
    market_snapshot: raw.market_snapshot ?? null,
    completeness: raw.completeness,
  };
}

export function useDashboard() {
  return useQuery({
    queryKey: ["candidate", "dashboard"],
    queryFn: () => api.get<CandidateDashboardWire>("/candidates/me/dashboard"),
    select: normalizeDashboard,
  });
}

/* ----------------------------------------------------------------------------
 * Trajectory Atlas
 * ------------------------------------------------------------------------- */

export interface AtlasRoute {
  id: string;
  title: string;
  occupation_id?: string;
  salary_range: SalaryRange;
  time_months: { min: number; max: number };
  feasibility: number;
  demand_trend: number;
  skill_gaps: SkillGap[];
  trade_offs: string[];
  glass_box: GlassBox;
}

export interface AtlasResponse {
  current: { occupation: string; occupation_id?: string };
  routes: AtlasRoute[];
  glass_box: GlassBox;
}

export function useAtlas() {
  return useMutation({
    mutationFn: (body: { horizon_years?: number }) =>
      api.post<AtlasResponse>("/ai/atlas", body),
  });
}

/* ----------------------------------------------------------------------------
 * Career Weather
 * ------------------------------------------------------------------------- */

export interface WeatherResponse {
  role: string;
  region: string;
  outlook: "sunny" | "cloudy" | "stormy";
  summary: string;
  demand_index: number;
  rising_skills: string[];
  cooling_skills: string[];
  salary_drift_pct: number;
  glass_box: GlassBox;
}

export function useWeather() {
  return useMutation({
    mutationFn: (body: { occupation_id?: string; region?: string }) =>
      api.post<WeatherResponse>("/ai/weather", body),
  });
}

/* ----------------------------------------------------------------------------
 * Fair Pay
 * ------------------------------------------------------------------------- */

export interface FairPayResponse {
  role: string;
  location: string;
  market: { p25: number; p50: number; p75: number; currency: string };
  your_pay?: number;
  gap_pct?: number;
  verdict: string;
  negotiation: { timing: string; script: string; talking_points: string[] };
  glass_box: GlassBox;
}

export function useFairPay() {
  return useMutation({
    mutationFn: (body: { occupation_id?: string; current_pay?: number }) =>
      api.post<FairPayResponse>("/ai/fair-pay", body),
  });
}

/* ----------------------------------------------------------------------------
 * Jobs & discovery
 * ------------------------------------------------------------------------- */

export interface JobSummary {
  id: string;
  title: string;
  company?: string;
  org_name?: string;
  location: string;
  work_mode?: string;
  seniority?: string;
  comp_min?: number;
  comp_max?: number;
  skills_required?: string[];
  posted_at?: string;
  match_score?: number;
}

export interface JobDetailResponse extends JobSummary {
  description: string;
  requirements?: string[];
  growth_into?: string[];
  currency?: string;
}

export interface JobMatch {
  score: number;
  sub_scores: {
    semantic: number;
    skill_overlap: number;
    trajectory_fit: number;
    salary_fit: number;
  };
  glass_box: GlassBox;
}

export interface JobFilters {
  q?: string;
  location?: string;
  seniority?: string;
  work_mode?: string;
  semantic?: boolean;
  page?: number;
}

export function useJobs(filters: JobFilters) {
  return useQuery({
    queryKey: ["candidate", "jobs", filters],
    queryFn: () =>
      api.get<Paginated<JobSummary>>("/jobs", {
        q: filters.q || undefined,
        location: filters.location || undefined,
        seniority: filters.seniority || undefined,
        work_mode: filters.work_mode || undefined,
        semantic: filters.semantic ? true : undefined,
        page: filters.page ?? 1,
      }),
  });
}

export function useJob(jobId: string | undefined) {
  return useQuery({
    queryKey: ["candidate", "job", jobId],
    queryFn: () => api.get<JobDetailResponse>(`/jobs/${jobId}`),
    enabled: !!jobId,
  });
}

export function useJobMatch(jobId: string | undefined) {
  return useQuery({
    queryKey: ["candidate", "job-match", jobId],
    queryFn: () => api.get<JobMatch>(`/jobs/${jobId}/match`),
    enabled: !!jobId,
  });
}

/* ----------------------------------------------------------------------------
 * Applications
 * ------------------------------------------------------------------------- */

export type ApplicationStatus =
  | "applied"
  | "screening"
  | "interview"
  | "offer"
  | "rejected"
  | "withdrawn";

export interface ApplicationEvent {
  status: ApplicationStatus | string;
  at: string;
  note?: string;
}

export interface Application {
  id: string;
  job_id: string;
  job_title: string;
  company?: string;
  org_name?: string;
  location?: string;
  status: ApplicationStatus | string;
  created_at: string;
  timeline?: ApplicationEvent[];
}

export function useApplications() {
  return useQuery({
    queryKey: ["candidate", "applications"],
    queryFn: () => api.get<Paginated<Application> | Application[]>("/applications"),
  });
}

export function useApply() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { job_id: string; cover_note?: string }) =>
      api.post<Application>("/applications", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["candidate", "applications"] });
    },
  });
}

/* ----------------------------------------------------------------------------
 * Profile
 * ------------------------------------------------------------------------- */

export interface CareerEvent {
  id: string;
  title: string;
  organization?: string;
  start_date?: string;
  end_date?: string | null;
  description?: string;
  kind?: string;
}

export interface CandidateSkill {
  skill: string;
  proficiency: number; // 0..1
  evidence?: string;
}

export interface CandidateProfile {
  id?: string;
  headline?: string;
  summary?: string;
  location?: string;
  aspirations?: string;
  target_occupation?: string;
  career_events: CareerEvent[];
  skills: CandidateSkill[];
  completeness: number; // 0..1 or 0..100
}

export interface ResumeParseResult {
  headline?: string;
  summary?: string;
  career_events: (CareerEvent & { confidence?: number })[];
  skills: (CandidateSkill & { confidence?: number })[];
  glass_box: GlassBox;
}

export function useProfile() {
  return useQuery({
    queryKey: ["candidate", "profile"],
    queryFn: () => api.get<CandidateProfile>("/candidates/me"),
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<CandidateProfile>) =>
      api.put<CandidateProfile>("/candidates/me", body),
    onSuccess: (data) => {
      qc.setQueryData(["candidate", "profile"], data);
    },
  });
}

export function useParseResume() {
  return useMutation({
    mutationFn: (text: string) =>
      api.post<ResumeParseResult>("/candidates/me/resume/parse", { text }),
  });
}

/* ----------------------------------------------------------------------------
 * Consent & data dignity
 * ------------------------------------------------------------------------- */

export interface ConsentGrant {
  id: string;
  grantee_org_id: string;
  grantee_org_name?: string;
  scopes: string[];
  purpose?: string;
  expires_at?: string | null;
  created_at?: string;
}

export interface AccessLogEntry {
  id: string;
  actor?: string;
  actor_org_name?: string;
  action: string;
  scope?: string;
  at: string;
}

export function useConsentGrants() {
  return useQuery({
    queryKey: ["candidate", "consent"],
    queryFn: () => api.get<ConsentGrant[] | Paginated<ConsentGrant>>("/consent"),
  });
}

export function useAccessLog() {
  return useQuery({
    queryKey: ["candidate", "consent", "access-log"],
    queryFn: () =>
      api.get<AccessLogEntry[] | Paginated<AccessLogEntry>>("/consent/access-log"),
  });
}

export function useGrantConsent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      grantee_org_id: string;
      scopes: string[];
      purpose?: string;
      expires_at?: string;
    }) => api.post<ConsentGrant>("/consent", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["candidate", "consent"] });
    },
  });
}

export function useRevokeConsent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/consent/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["candidate", "consent"] });
    },
  });
}

/* ----------------------------------------------------------------------------
 * Helpers
 * ------------------------------------------------------------------------- */

/** Tolerate either a Paginated<T> envelope or a bare array from the API. */
export function asArray<T>(data: Paginated<T> | T[] | undefined): T[] {
  if (!data) return [];
  return Array.isArray(data) ? data : data.items ?? [];
}

/** Normalise a 0..1 or 0..100 completeness value to a 0..100 percentage. */
export function toPercent100(value: number | undefined): number {
  if (value == null) return 0;
  return value <= 1 ? Math.round(value * 100) : Math.round(value);
}
