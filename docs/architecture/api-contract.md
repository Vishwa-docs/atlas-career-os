# Atlas API Contract (v1)

**Authoritative interface.** Backend implements it; frontend consumes it. Both sides
follow this document so the parallel build stays coherent. Base path: `/api/v1`.

## Conventions
- **Auth:** `Authorization: Bearer <access_token>`. Login issues `{access_token, refresh_token, token_type:"bearer"}`.
- **Errors:** `{ "error": { "code": string, "message": string, "details"?: any } }` with appropriate HTTP status.
- **IDs:** UUID strings. **Timestamps:** ISO-8601 UTC.
- **Pagination:** list endpoints accept `?page=1&page_size=20`; return `{ items: [...], total, page, page_size }`.
- **Glass Box:** every AI judgement embeds:
  ```json
  { "rationale": "…", "confidence": "low|medium|high", "confidence_score": 0.0,
    "citations": [{"label":"…","source_type":"salary_data","source_id":null,"snippet":"…","url":null}],
    "what_would_change_this": ["…"], "caveats": ["…"] }
  ```

## Auth & users
| Method | Path | Body / Notes | Returns |
|---|---|---|---|
| POST | `/auth/register` | `{email,password,full_name,role,org_name?}` | `201 {user}` |
| POST | `/auth/login` | form: `username`(email),`password` | `{access_token,refresh_token,token_type}` |
| POST | `/auth/refresh` | `{refresh_token}` | new token pair (rotates) |
| POST | `/auth/logout` | — | `204` (revokes refresh) |
| GET | `/auth/me` | — | `{id,email,full_name,roles[],org_id,org_name?,locale,avatar_url?}` |

`role` ∈ candidate · employer_admin · employer_recruiter · university_admin · university_staff. Registering an employer/university creates the Organization and an admin membership.

## Candidate · Navigator
| Method | Path | Returns / Notes |
|---|---|---|
| GET | `/candidates/me` | full profile + career events + skills + completeness |
| PUT | `/candidates/me` | update headline/summary/location/aspirations/target |
| POST | `/candidates/me/resume/parse` | multipart or `{text}` → LLM-parsed structured graph (with Glass Box per inference); does not auto-commit |
| POST | `/candidates/me/career-events` / PUT/DELETE `/{id}` | CRUD career timeline |
| GET/PUT | `/candidates/me/skills` | candidate skills (proficiency, evidence) |
| GET | `/candidates/me/dashboard` | `{stats, recent_matches[], nudges[], market_snapshot}` |
| GET | `/candidates/{id}` | employer/university view — **consent-gated** |

## Taxonomy
- `GET /taxonomy/skills?q=&category=` → skills (paginated)
- `GET /taxonomy/occupations?q=` → occupations
- `GET /taxonomy/occupations/{id}` → occupation + skills + median salary

## Jobs & search
- `GET /jobs?q=&location=&seniority=&work_mode=&semantic=true&page=` → hybrid search (vector+BM25+RRF when `semantic`), `{items:[job], total,...}`
- `GET /jobs/{id}` → job detail
- `GET /jobs/{id}/match` → candidate's explained match: `{score, sub_scores:{semantic,skill_overlap,trajectory_fit,salary_fit}, glass_box}`
- `POST /jobs` (employer) `{title,description,occupation_id?,requirements[],skills_required[],location,work_mode,seniority,comp_min,comp_max,growth_into[]}`; `PUT/DELETE /jobs/{id}`
- `POST /jobs/{id}/debias` (employer) → `{rewritten, issues:[{phrase,why,suggestion}], glass_box}` (Bias Auditor)

## Applications
- `POST /applications` `{job_id, cover_note?}` → application
- `GET /applications` (candidate) → list with job + status timeline
- `GET /jobs/{job_id}/applications` (employer) → pipeline for a job
- `PATCH /applications/{id}/status` (employer) `{status, note?, feedback?}` → updates + appends event

## Matching
- `GET /matching/jobs?limit=` (candidate) → top explained job matches `[{job, score, sub_scores, glass_box}]`
- `GET /matching/candidates?job_id=&q=&limit=` (employer) → trajectory-aware, consent-gated candidate matches `[{candidate_summary, score, sub_scores, glass_box}]`

## AI · signature features (all return Glass Box)
- `POST /ai/coach` `{message, history?[]}` → `{message, glass_box}` ; `POST /ai/coach/stream` → **SSE** frames `data: {"delta":"…"}` … `data: [DONE]`
- `POST /ai/atlas` `{horizon_years?}` → Trajectory Atlas:
  ```json
  { "current": {"occupation":"…","occupation_id":"…"},
    "routes": [ { "id":"…","title":"…","occupation_id":"…",
      "salary_range":{"min":0,"max":0,"median":0,"currency":"MYR"},
      "time_months":{"min":0,"max":0}, "feasibility":0.0, "demand_trend":0.0,
      "skill_gaps":[{"skill":"…","have":0.0,"need":0.0}],
      "trade_offs":["…"], "glass_box":{…} } ],
    "glass_box": {…} }
  ```
- `POST /ai/fair-pay` `{occupation_id?, current_pay?}` → `{role, location, market:{p25,p50,p75,currency}, your_pay?, gap_pct?, verdict, negotiation:{timing, script, talking_points[]}, glass_box}`
- `POST /ai/weather` `{occupation_id?, region?}` → `{role, region, outlook:"sunny|cloudy|stormy", summary, demand_index, rising_skills[], cooling_skills[], salary_drift_pct, glass_box}`
- `POST /ai/pivot` `{target_occupation_id}` → `{feasibility, gap:[{skill,have,need}], ramp:[{step,resource,months}], glass_box}`

## Consent & data dignity
- `GET /consent` → my grants ; `POST /consent` `{grantee_org_id, scopes[], purpose?, expires_at?}` ; `DELETE /consent/{id}` (revoke)
- `GET /consent/access-log` → who viewed what (from audit log)
- `GET /me/export` → full data export (JSON) ; `DELETE /me` → erasure

## Signals (employer)
- `GET /signals?type=&status=` → retention/onboarding signals with evidence + Glass Box
- `PATCH /signals/{id}` `{status}` → acknowledge/action/dismiss
- `GET /employers/onboarding` → first-60-day risk list
- `GET /employers/reengagement` → warm-bench candidates (opt-in)
- `GET /employers/workforce` → UN-WPP-based scenarios `{country, projections:[{year, working_age, supply_index}], scenarios:[…], glass_box}`
- `GET /employers/me/dashboard` → `{open_roles, pipeline, time_to_fill, flight_risk_count, ...}`

## University · Outcomes Studio
- `GET /universities/me/dashboard` → headline outcome stats
- `GET /universities/outcomes?cohort=&year=` → outcomes analytics `{employment_rate, median_salary, median_months_to_employ, by_field[], trend[]}`
- `GET /universities/students` → roster + readiness scores
- `GET /universities/students/{candidate_id}/readiness` → Adaptive Readiness Profile `{score, dimensions[], glass_box}`
- `GET /universities/curriculum` → Future-State Curriculum gaps `{program, market_skills[], covered[], gaps[], glass_box}`
- `GET /universities/internships` / `POST` → internship marketplace
- `POST /universities/credentials` (issue) ; `GET /credentials/verify/{id}` (verify proof)

## Admin · Mission Control
- `GET /admin/metrics` → platform KPIs
- `GET /admin/tenants` / `GET /admin/users` (paginated)
- `GET /admin/taxonomy` → counts + management
- `GET /admin/ai-usage` → `{total_cost_usd, by_feature[], by_day[], tokens}`
- `GET /admin/audit?actor=&action=` → audit log (paginated)

## Notifications
- `GET /notifications` → list ; `PATCH /notifications/{id}/read` ; `WS /ws/notifications` (auth via `?token=`) → live pushes
