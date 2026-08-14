# API Reference

> **Status: as built.** Written from `backend/app/api/v1/` and verified against the running
> server. Supersedes the pre-implementation draft, which described a `202 Accepted` + `task_id`
> upload flow, `res_123`-style string ids, and an `/ats/score` endpoint — none of which exist.

Base URL: `http://localhost:8000/api/v1`. Interactive docs at `/docs`; raw spec at
`/api/v1/openapi.json`.

## Authentication

Every data endpoint requires a bearer token. Only `/auth/signup`, `/auth/login`, and `/health`
are public.

```
Authorization: Bearer <access_token>
```

| Condition | Response |
|---|---|
| No token, or an invalid, expired, or forged one | `401` |
| Valid token, but the record belongs to another user | `404` |

The cross-account case returns **404 rather than 403 deliberately** — a 403 would confirm the
record exists. Ownership is resolved by `app/api/deps.py::get_current_user`; alignments and
resume versions inherit it through their resume.

---

## Auth

### `POST /auth/signup`
```json
{ "email": "you@example.com", "password": "…", "full_name": "Your Name" }
```
`200` → `UserOut`. `400` if the email is already registered. Email is lowercased.

### `POST /auth/login`
Form-encoded (OAuth2 password flow): `username`, `password`.

`200` → `{ "access_token": "...", "token_type": "bearer" }`. `400` on bad credentials.

---

## Resumes

### `POST /resume/upload`
`multipart/form-data` — `file` (required), `label` (optional).

`200` → `ResumeOut` with `structured_data` and `extraction_meta`.

| Status | When |
|---|---|
| `400` | Empty file |
| `413` | Over 5 MB |
| `415` | Not a PDF, DOCX, or text file (detected by magic bytes, not extension) |
| `422` | No readable text — e.g. a scanned PDF with no text layer |

**Idempotent.** Identical bytes return the existing record with `duplicate_of_existing: true`, no
second file on disk and no re-parse.

### `GET /resume/list`
`?skip=0&limit=50` (max 100). Returns the caller's resumes.

### `GET /resume/{resume_id}`
`404` if unknown or owned by someone else.

### `POST /resume/optimize`
```json
{ "resume_id": "uuid", "jd_id": "uuid", "focus_area": null }
```
`200` → `OptimizeResponse`: `version_id`, `version_number`, before/after scores with deltas,
`changes` (with before/after text per rewrite), `suggestions`, `blocked_rewrites`, `used_llm`,
`from_cache`, `note`, `scoring_note`, and both download URLs.

`422` if the resume has no readable experience or skills. `404` if either id is unknown or not
yours.

Before/after are scored **deterministically** so the comparison is like-for-like; `scoring_note`
explains why this can differ slightly from the alignment score.

### `GET /resume/{resume_id}/versions`
Tailored variants, newest version first.

### `GET /resume/versions/{version_id}/download?format=docx|pdf`
Streams the file. `422` for any other format, `404` if the version is unknown, not yours, or the
file is missing from disk.

---

## Job descriptions

### `POST /jd/upload`
```json
{ "raw_text": "…full posting…", "title": "", "company_name": "", "url": null }
```
`200` → `JDOut`. `422` if `raw_text` is empty.

Placeholder values for `title` / `company_name` (`"Target Role"`, `"Company"`, `""`, …) are
ignored in favour of the parsed role and company. `url` is **stored but never fetched**.

Deduped on a hash of `raw_text`: the same posting twice returns the first row.

### `GET /jd/list` · `GET /jd/{jd_id}`
Same pagination and ownership rules as resumes.

---

## Alignment

### `POST /alignment/generate`
```json
{ "resume_id": "uuid", "jd_id": "uuid" }
```
`200` → `AlignmentResponseSchema`:

```json
{
  "alignment_id": "uuid",
  "alignment_score": 68.3,
  "ats_score": 79.17,
  "breakdown": { "skill_match": 89.09, "responsibility_match": 100.0,
                 "project_match": 0.0, "seniority_match": 63.33 },
  "component_weights": { "skill_match": 0.4, "…": 0.2 },
  "matched_skills": ["Python", "FastAPI"],
  "partial_skills": [{ "skill": "Kubernetes", "covered_by": "Docker" }],
  "missing_skills": [{ "skill": "Kafka", "importance": "preferred",
                       "priority": "P3", "weight": 0.25 }],
  "missing_keywords": ["Kafka"],
  "ats_breakdown": { "keyword_coverage": 57.14, "…": 100.0 },
  "ats_warnings": ["…"],
  "feedback": "…",
  "improvement_suggestions": ["…"],
  "extraction_health": { "resume_ok": true, "jd_ok": true, "warnings": [] }
}
```

Every run appends a row, so history is preserved. `extraction_health` distinguishes a genuinely
weak match from a failed parse — without it a `0%` score is ambiguous.

### `GET /alignment/list`
`?resume_id=&jd_id=&latest_only=false&skip=0&limit=50`

Scores and timestamps only, newest first. `latest_only=true` collapses to the newest run per
resume/JD pair.

### `GET /alignment/{alignment_id}`
The full stored analysis for one run.

---

## Analytics

### `GET /dashboard/summary`
Totals, average and best scores, `career_readiness_index`, `interview_probability`,
`top_skill_gaps` with detail, `readiness_trend`, `top_company_matches` (one row per company),
`recent_activity`, `recommended_improvements`, and `has_data`.

`has_data` is `false` for an account with no alignment runs, so the UI can show an empty state
rather than a grid of zeros.

`interview_probability` ships its own `basis` and `caveat`: it is a heuristic over the user's own
scores, **not** a model trained on hiring outcomes.

### `GET /learning/roadmap`
Modules clustered by skill category, ordered by priority then prerequisite, each with an ETA and
official documentation links. With no gaps it returns an empty plan and a `note` explaining why.

### `GET /company/{companyId}/insights`
Accepts a company name or its slug. Reports only what the caller's saved postings say: roles,
seniority, locations, work modes, demanded skills, their alignment history, and gaps specific to
that company.

`404` when no saved posting matches — the endpoint reports nothing it cannot trace to a real
posting.

---

## Health

### `GET /health`
`{ "status": "healthy", "db": "connected", "redis": "in-memory-fallback" }`. Unauthenticated.

---

## Conventions

- All ids are UUIDs.
- Scores are floats on a **0–100** scale.
- Lists return bare JSON arrays with `skip` / `limit` (max 100); there is no total count.
- Errors are FastAPI's `{ "detail": "..." }`.
- Processing is **synchronous** — there is no task queue and no `task_id`.
- No delete or update endpoints exist for any resource.
