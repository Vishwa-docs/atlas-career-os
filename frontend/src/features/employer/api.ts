/**
 * Employer (Talent Radar) data layer.
 * Local interfaces mirror docs/architecture/api-contract.md. All hooks call the
 * shared typed `api` client and use stable query keys for cache coherence.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/apiClient";
import type { GlassBox, Paginated } from "@/types/api";

/* ----------------------------------------------------------------------------
 * Shared helpers
 * ------------------------------------------------------------------------- */

/** Tolerate either a Paginated<T> envelope or a bare array from the API. */
export function asArray<T>(data: Paginated<T> | T[] | undefined): T[] {
  if (!data) return [];
  return Array.isArray(data) ? data : data.items ?? [];
}

/* ----------------------------------------------------------------------------
 * Dashboard — GET /employers/me/dashboard
 * ------------------------------------------------------------------------- */

export interface PipelineStage {
  stage: string;
  count: number;
}

export interface DashboardActivity {
  id: string;
  kind?: string;
  title: string;
  detail?: string;
  at: string;
}

export interface EmployerDashboard {
  open_roles: number;
  pipeline: PipelineStage[];
  time_to_fill: number | null; // days
  flight_risk_count: number;
  applications_total?: number;
  offers_out?: number;
  recent_activity?: DashboardActivity[];
}

export function useEmployerDashboard() {
  return useQuery({
    queryKey: ["employer", "dashboard"],
    queryFn: () => api.get<EmployerDashboard>("/employers/me/dashboard"),
  });
}

/* ----------------------------------------------------------------------------
 * Talent Search — GET /matching/candidates?job_id&q
 * ------------------------------------------------------------------------- */

export interface CandidateSummary {
  id: string;
  full_name: string;
  headline?: string;
  location?: string;
  current_role?: string;
  top_skills?: string[];
  years_experience?: number;
  avatar_url?: string | null;
}

export interface CandidateMatch {
  candidate_summary: CandidateSummary;
  score: number;
  sub_scores: {
    semantic: number;
    skill_overlap: number;
    trajectory_fit: number;
    salary_fit: number;
  };
  glass_box: GlassBox;
  consent_note?: string;
}

export function useCandidateMatches(params: { job_id?: string; q?: string; limit?: number }) {
  return useQuery({
    queryKey: ["employer", "candidate-matches", params],
    queryFn: () =>
      api.get<CandidateMatch[]>("/matching/candidates", {
        job_id: params.job_id || undefined,
        q: params.q || undefined,
        limit: params.limit ?? 20,
      }),
    enabled: !!params.job_id || !!params.q,
  });
}

/* ----------------------------------------------------------------------------
 * Jobs — GET /jobs (org), POST /jobs, POST /jobs/:id/debias
 * ------------------------------------------------------------------------- */

export interface EmployerJob {
  id: string;
  title: string;
  description?: string;
  location: string;
  work_mode?: string;
  seniority?: string;
  comp_min?: number;
  comp_max?: number;
  currency?: string;
  skills_required?: string[];
  requirements?: string[];
  status?: string;
  applicant_count?: number;
  posted_at?: string;
}

export interface CreateJobInput {
  title: string;
  description: string;
  location: string;
  work_mode?: string;
  seniority?: string;
  comp_min?: number;
  comp_max?: number;
  skills_required?: string[];
  requirements?: string[];
}

export interface DebiasIssue {
  phrase: string;
  why: string;
  suggestion: string;
}

export interface DebiasResult {
  rewritten: string;
  issues: DebiasIssue[];
  glass_box: GlassBox;
}

export function useEmployerJobs() {
  return useQuery({
    queryKey: ["employer", "jobs"],
    queryFn: () => api.get<Paginated<EmployerJob> | EmployerJob[]>("/jobs", { mine: true }),
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateJobInput) => api.post<EmployerJob>("/jobs", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["employer", "jobs"] });
    },
  });
}

export function useDebiasJob() {
  return useMutation({
    mutationFn: (jobId: string) => api.post<DebiasResult>(`/jobs/${jobId}/debias`),
  });
}

/* ----------------------------------------------------------------------------
 * Pipeline — GET /jobs/:id/applications, PATCH /applications/:id/status
 * ------------------------------------------------------------------------- */

export type PipelineStatus =
  | "applied"
  | "screening"
  | "interview"
  | "offer"
  | "rejected"
  | "withdrawn";

export interface PipelineApplication {
  id: string;
  candidate_id?: string;
  candidate_name: string;
  headline?: string;
  status: PipelineStatus | string;
  match_score?: number;
  applied_at?: string;
  avatar_url?: string | null;
}

export function useJobApplications(jobId: string | undefined) {
  return useQuery({
    queryKey: ["employer", "applications", jobId],
    queryFn: () =>
      api.get<Paginated<PipelineApplication> | PipelineApplication[]>(
        `/jobs/${jobId}/applications`,
      ),
    enabled: !!jobId,
  });
}

export function useMoveApplication(jobId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id: string; status: PipelineStatus | string; note?: string }) =>
      api.patch<PipelineApplication>(`/applications/${input.id}/status`, {
        status: input.status,
        note: input.note,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["employer", "applications", jobId] });
    },
  });
}

/* ----------------------------------------------------------------------------
 * Retention Signals — GET /signals, PATCH /signals/:id
 * ------------------------------------------------------------------------- */

export type SignalStatus = "open" | "acknowledged" | "actioned" | "dismissed";

export interface SignalEvidence {
  label: string;
  detail?: string;
}

export interface RetentionSignal {
  id: string;
  type?: string;
  subject_name?: string;
  title: string;
  summary?: string;
  severity?: "low" | "medium" | "high";
  status: SignalStatus | string;
  evidence?: SignalEvidence[];
  glass_box: GlassBox;
  detected_at?: string;
}

export function useSignals(params?: { type?: string; status?: string }) {
  return useQuery({
    queryKey: ["employer", "signals", params ?? {}],
    queryFn: () =>
      api.get<Paginated<RetentionSignal> | RetentionSignal[]>("/signals", {
        type: params?.type || undefined,
        status: params?.status || undefined,
      }),
  });
}

export function useUpdateSignal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id: string; status: SignalStatus }) =>
      api.patch<RetentionSignal>(`/signals/${input.id}`, { status: input.status }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["employer", "signals"] });
    },
  });
}

/* ----------------------------------------------------------------------------
 * Re-Engagement — GET /employers/reengagement
 * ------------------------------------------------------------------------- */

export interface WarmBenchCandidate {
  id: string;
  full_name: string;
  headline?: string;
  former_role?: string;
  reason?: string;
  last_contact?: string;
  fit_score?: number;
  avatar_url?: string | null;
  glass_box?: GlassBox;
}

export function useReEngagement() {
  return useQuery({
    queryKey: ["employer", "reengagement"],
    queryFn: () =>
      api.get<Paginated<WarmBenchCandidate> | WarmBenchCandidate[]>(
        "/employers/reengagement",
      ),
  });
}

/* ----------------------------------------------------------------------------
 * Onboarding Risk — GET /employers/onboarding
 * ------------------------------------------------------------------------- */

export interface OnboardingRiskItem {
  id: string;
  full_name: string;
  role?: string;
  start_date?: string;
  days_in?: number;
  risk_level?: "low" | "medium" | "high";
  risk_score?: number;
  glass_box: GlassBox;
  avatar_url?: string | null;
}

export function useOnboardingRisk() {
  return useQuery({
    queryKey: ["employer", "onboarding"],
    queryFn: () =>
      api.get<Paginated<OnboardingRiskItem> | OnboardingRiskItem[]>(
        "/employers/onboarding",
      ),
  });
}

/* ----------------------------------------------------------------------------
 * Workforce Resilience — GET /employers/workforce
 * ------------------------------------------------------------------------- */

export interface WorkforceProjection {
  year: number;
  working_age: number;
  supply_index: number;
}

export interface WorkforceScenario {
  id: string;
  title: string;
  description?: string;
  impact?: string;
  horizon_years?: number;
  delta_pct?: number;
}

export interface WorkforceResponse {
  country: string;
  projections: WorkforceProjection[];
  scenarios: WorkforceScenario[];
  glass_box: GlassBox;
}

export function useWorkforce() {
  return useQuery({
    queryKey: ["employer", "workforce"],
    queryFn: () => api.get<WorkforceResponse>("/employers/workforce"),
  });
}
