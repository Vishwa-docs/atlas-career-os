/**
 * University (Outcomes Studio) data layer.
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
 * Dashboard — GET /universities/me/dashboard
 * ------------------------------------------------------------------------- */

export interface OutcomeTrendPoint {
  year: number;
  employment_rate: number;
  median_salary?: number;
}

export interface UniversityDashboard {
  employment_rate: number;
  median_salary: number;
  median_months_to_employ: number;
  active_students: number;
  graduates_tracked?: number;
  programs?: number;
  internships_open?: number;
  credentials_issued?: number;
  currency?: string;
  trend?: OutcomeTrendPoint[];
}

export function useUniversityDashboard() {
  return useQuery({
    queryKey: ["university", "dashboard"],
    queryFn: () => api.get<UniversityDashboard>("/universities/me/dashboard"),
  });
}

/* ----------------------------------------------------------------------------
 * Outcome Loop — GET /universities/outcomes?cohort&year
 * ------------------------------------------------------------------------- */

export interface OutcomeByField {
  field: string;
  employment_rate: number;
  median_salary: number;
  graduates?: number;
  median_months_to_employ?: number;
}

export interface OutcomeTrendYear {
  year: number;
  employment_rate: number;
  median_salary?: number;
  median_months_to_employ?: number;
}

export interface OutcomesResponse {
  employment_rate: number;
  median_salary: number;
  median_months_to_employ: number;
  currency?: string;
  by_field: OutcomeByField[];
  trend: OutcomeTrendYear[];
  glass_box?: GlassBox;
}

export function useOutcomes(params?: { cohort?: string; year?: number }) {
  return useQuery({
    queryKey: ["university", "outcomes", params ?? {}],
    queryFn: () =>
      api.get<OutcomesResponse>("/universities/outcomes", {
        cohort: params?.cohort || undefined,
        year: params?.year || undefined,
      }),
  });
}

/* ----------------------------------------------------------------------------
 * Students — GET /universities/students
 * ------------------------------------------------------------------------- */

export interface UniversityStudent {
  id: string;
  full_name: string;
  program?: string;
  field?: string;
  year?: number | string;
  cohort?: string;
  readiness_score?: number;
  status?: string;
  email?: string;
  avatar_url?: string | null;
}

export function useStudents(params?: { q?: string; program?: string }) {
  return useQuery({
    queryKey: ["university", "students", params ?? {}],
    queryFn: () =>
      api.get<Paginated<UniversityStudent> | UniversityStudent[]>("/universities/students", {
        q: params?.q || undefined,
        program: params?.program || undefined,
      }),
  });
}

/* ----------------------------------------------------------------------------
 * Readiness Profile — GET /universities/students/:id/readiness
 * ------------------------------------------------------------------------- */

export interface ReadinessDimension {
  name: string;
  score: number;
  benchmark?: number;
  detail?: string;
}

export interface ReadinessProfile {
  score: number;
  student_name?: string;
  program?: string;
  dimensions: ReadinessDimension[];
  glass_box: GlassBox;
}

export function useReadiness(studentId: string | undefined) {
  return useQuery({
    queryKey: ["university", "readiness", studentId],
    queryFn: () =>
      api.get<ReadinessProfile>(`/universities/students/${studentId}/readiness`),
    enabled: !!studentId,
  });
}

/* ----------------------------------------------------------------------------
 * Curriculum Engine — GET /universities/curriculum
 * ------------------------------------------------------------------------- */

export interface MarketSkill {
  skill: string;
  demand?: number; // 0..1 market demand intensity
  coverage?: number; // 0..1 how well the curriculum covers it
}

export interface CurriculumGap {
  skill: string;
  demand?: number;
  severity?: "low" | "medium" | "high";
  recommendation?: string;
}

export interface CurriculumResponse {
  program: string;
  market_skills: MarketSkill[];
  covered: string[];
  gaps: CurriculumGap[];
  glass_box: GlassBox;
}

export function useCurriculum(program?: string) {
  return useQuery({
    queryKey: ["university", "curriculum", program ?? ""],
    queryFn: () =>
      api.get<CurriculumResponse>("/universities/curriculum", {
        program: program || undefined,
      }),
  });
}

/* ----------------------------------------------------------------------------
 * Internships — GET/POST /universities/internships
 * ------------------------------------------------------------------------- */

export interface Internship {
  id: string;
  title: string;
  employer?: string;
  org_name?: string;
  location?: string;
  work_mode?: string;
  field?: string;
  stipend_min?: number;
  stipend_max?: number;
  currency?: string;
  duration_months?: number;
  openings?: number;
  applicants?: number;
  status?: string;
  posted_at?: string;
  description?: string;
}

export interface CreateInternshipInput {
  title: string;
  employer: string;
  location: string;
  work_mode?: string;
  field?: string;
  duration_months?: number;
  openings?: number;
  stipend_min?: number;
  stipend_max?: number;
  description?: string;
}

export function useInternships() {
  return useQuery({
    queryKey: ["university", "internships"],
    queryFn: () =>
      api.get<Paginated<Internship> | Internship[]>("/universities/internships"),
  });
}

export function useCreateInternship() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateInternshipInput) =>
      api.post<Internship>("/universities/internships", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["university", "internships"] });
    },
  });
}

/* ----------------------------------------------------------------------------
 * Credentials — POST /universities/credentials, GET /credentials/verify/:id
 * ------------------------------------------------------------------------- */

export interface IssueCredentialInput {
  recipient_name: string;
  recipient_email?: string;
  credential_type: string;
  title: string;
  program?: string;
  issued_on?: string;
}

export interface Credential {
  id: string;
  recipient_name: string;
  credential_type?: string;
  title: string;
  program?: string;
  issuer?: string;
  issued_on?: string;
  verification_url?: string;
  proof_hash?: string;
}

export interface VerifyCredentialResult {
  valid: boolean;
  credential?: Credential;
  issuer?: string;
  issued_on?: string;
  revoked?: boolean;
  message?: string;
  glass_box?: GlassBox;
}

export function useIssueCredential() {
  return useMutation({
    mutationFn: (body: IssueCredentialInput) =>
      api.post<Credential>("/universities/credentials", body),
  });
}

export function useVerifyCredential() {
  return useMutation({
    mutationFn: (id: string) =>
      api.get<VerifyCredentialResult>(`/credentials/verify/${encodeURIComponent(id)}`),
  });
}
