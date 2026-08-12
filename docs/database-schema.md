# Database Schema

> **Status: as built.** Generated from `backend/app/models/` and verified against the applied
> migrations. Supersedes the pre-implementation draft, which documented a `user_id` column that is
> actually `owner_id`, an `embedding VECTOR(3072)` column that was never created, and omitted
> three tables.

PostgreSQL, accessed through SQLAlchemy 2.0 with `asyncpg`. **`pgvector` is not in use** — no
table has an embedding column, and no semantic search is implemented.

## Common columns

Every table inherits these from `app/db/base.py`:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key, indexed, defaults to `uuid4` |
| `created_at` | TIMESTAMP | Indexed, defaults to now |
| `updated_at` | TIMESTAMP | Updated on write |
| `is_deleted` | BOOLEAN | Indexed. Soft delete — **every read filters on it** |

Nothing is ever hard-deleted; `BaseRepository.remove` sets `is_deleted`.

## Relationships

```text
users 1─N resumes            (resumes.owner_id)
users 1─N job_descriptions   (job_descriptions.owner_id)
users 1─N skill_gaps, learning_paths, dashboard_snapshots

resumes          1─N alignment_scores  (alignment_scores.resume_id)
job_descriptions 1─N alignment_scores  (alignment_scores.jd_id)
resumes          1─N resume_versions   (resume_versions.resume_id)
job_descriptions 1─N resume_versions   (resume_versions.jd_id, nullable)

llm_cache        standalone, keyed by content hash
```

**Ownership is only on `resumes` and `job_descriptions`.** `alignment_scores` and
`resume_versions` have no owner column and inherit it through `resume_id` — queries constrain
them with a subquery over owned resumes. See `AlignmentRepository._owned_resume_ids`.

---

## `users`

| Column | Type | Notes |
|---|---|---|
| `email` | VARCHAR | Unique, indexed. Normalised to lowercase on signup and login |
| `hashed_password` | VARCHAR | bcrypt via passlib |
| `full_name` | VARCHAR | |
| `is_active` | BOOLEAN | A false value fails token resolution |
| `is_superuser` | BOOLEAN | Not used by any route yet |

## `resumes`

| Column | Type | Notes |
|---|---|---|
| `owner_id` | UUID FK → users.id | Not null. Scopes every read |
| `filename` | VARCHAR | Not null. Original upload name |
| `label` | VARCHAR | User-supplied name |
| `s3_path` | VARCHAR | Local path today; the storage adapter is pluggable |
| `content_hash` | VARCHAR | Indexed. SHA-256 of the bytes — the upload dedupe key |
| `raw_text` | VARCHAR | Cleaned text from the extraction pipeline |
| `structured_data` | JSON | `ResumeStructuredData`, tagged `schema_version` |
| `extraction_meta` | JSON | Method, page/word count, confidence, warnings, and a nested `structuring` block |

Re-uploading identical bytes returns the existing row rather than writing a second copy.

## `job_descriptions`

| Column | Type | Notes |
|---|---|---|
| `owner_id` | UUID FK → users.id | Not null |
| `title` | VARCHAR | Not null. Parsed role wins over a placeholder from the client |
| `company_name` | VARCHAR | Same placeholder rule |
| `raw_text` | VARCHAR | The pasted posting |
| `content_hash` | VARCHAR | Indexed. SHA-256 of `raw_text` — dedupe key |
| `structured_data` | JSON | `JDStructuredData`, tagged `schema_version` |
| `url` | VARCHAR | Stored for reference. **Never fetched** |

## `alignment_scores`

One row per scoring run — history is appended, never overwritten.

| Column | Type | Notes |
|---|---|---|
| `resume_id` | UUID FK → resumes.id | Not null. Also the ownership path |
| `jd_id` | UUID FK → job_descriptions.id | Not null |
| `total_alignment_score` | FLOAT | Exposed by the API as `alignment_score` |
| `ats_score` | FLOAT | |
| `skill_match_score` | FLOAT | |
| `experience_match_score` | FLOAT | |
| `cultural_fit_score` | FLOAT | **Never populated** — no data supports it |
| `analysis_data` | JSON | Breakdown, weights, matched/partial/missing skills, ATS breakdown and warnings, feedback, suggestions, extraction health |

## `resume_versions`

| Column | Type | Notes |
|---|---|---|
| `resume_id` | UUID FK → resumes.id | Not null |
| `version_number` | INTEGER | Not null. Counts from 1 per resume, never reused |
| `jd_id` | UUID FK → job_descriptions.id | Nullable |
| `label` | VARCHAR | e.g. `v1 tailored for Acme - Senior Backend Engineer` |
| `filename` | VARCHAR | Not null |
| `s3_path` | VARCHAR | Generated `.docx` |
| `pdf_path` | VARCHAR | Generated PDF |
| `changes_applied` | JSON | Change log, with before/after text per rewrite |
| `optimized_data` | JSON | The tailored resume, same shape as `resumes.structured_data` |
| `ats_score`, `alignment_score` | FLOAT | Scores for this variant |
| `baseline_ats_score`, `baseline_alignment_score` | FLOAT | The originals, so the delta is recoverable |

Both score pairs are computed deterministically, so before/after is like-for-like.

## `llm_cache`

| Column | Type | Notes |
|---|---|---|
| `cache_key` | VARCHAR | Unique, indexed. SHA-256 of the feature plus its inputs |
| `feature` | VARCHAR | Indexed |
| `payload` | JSON | The **raw model response**, not a verdict — validation re-runs on read |

Free-tier model quotas are metered per day, so this is persisted rather than held in memory.

## Unused tables

These exist from the original design and are **written by nothing**. Skill gaps, roadmaps, and
dashboard metrics are computed on read instead.

| Table | Columns |
|---|---|
| `skill_gaps` | `user_id`, `missing_skills` JSON, `priority_skills` JSON |
| `learning_paths` | `user_id`, `roadmap_data` JSON, `progress_percentage` FLOAT |
| `dashboard_snapshots` | `user_id`, `snapshot_data` JSON |

## Indexes

Beyond the primary keys and the inherited `created_at` / `is_deleted` indexes:

- `users.email` — unique, for login
- `resumes.content_hash`, `job_descriptions.content_hash` — upload dedupe
- `llm_cache.cache_key` (unique), `llm_cache.feature`

No HNSW or vector index exists; the earlier draft's `idx_resumes_embedding` was never created.

## Migrations

| Revision | Adds |
|---|---|
| `92f9b5ffe7fc` | Initial tables |
| `a1c4e7d92b30` | `resumes.label`, `content_hash`, `extraction_meta` |
| `b7d2f1a4c803` | `resume_versions`: label, pdf_path, optimized_data, and the four score columns |
| `c3a9e5b71f42` | `llm_cache` table, `job_descriptions.content_hash` |

```bash
cd backend && ../.venv/bin/python -m alembic upgrade head
```
