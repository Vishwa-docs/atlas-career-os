/**
 * Shared API types mirroring the backend Pydantic schemas.
 * The Glass Box envelope is the most important shared contract: every AI output
 * carries it, and `<GlassBoxPanel>` renders it uniformly.
 */

export type Role =
  | "candidate"
  | "employer_recruiter"
  | "employer_admin"
  | "university_staff"
  | "university_admin"
  | "platform_admin";

export interface User {
  id: string;
  email: string;
  full_name: string;
  roles: Role[];
  org_id: string | null;
  org_name?: string | null;
  locale: "en" | "ms" | "zh";
  avatar_url?: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export type Confidence = "low" | "medium" | "high";

export type CitationSourceType =
  | "career_history"
  | "job_posting"
  | "salary_data"
  | "skill_taxonomy"
  | "labor_market"
  | "cohort_data"
  | "demographic_data"
  | "user_input";

export interface Citation {
  label: string;
  source_type: CitationSourceType;
  source_id?: string | null;
  snippet?: string | null;
  url?: string | null;
}

export interface GlassBox {
  rationale: string;
  confidence: Confidence;
  confidence_score: number;
  citations: Citation[];
  what_would_change_this: string[];
  caveats: string[];
}

export interface ApiError {
  error: { code: string; message: string; details?: unknown };
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
