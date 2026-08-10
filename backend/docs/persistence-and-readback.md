# Persistence and read-back

> Delivered in Phase 5. Phase 4 stored the full analysis; this makes it readable, keeps a
> history of every run, and stops the same file being stored twice.

## Endpoint reference

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/resume/upload` | Upload a resume. Idempotent — see [Upload dedupe](#upload-dedupe) |
| `GET` | `/api/v1/resume/list` | Resumes, `?skip=&limit=` |
| `GET` | `/api/v1/resume/{id}` | One resume with `structured_data` and `extraction_meta` |
| `POST` | `/api/v1/jd/upload` | Upload a JD. `422` if `raw_text` is empty |
| `GET` | `/api/v1/jd/list` | Job descriptions, `?skip=&limit=` |
| `GET` | `/api/v1/jd/{id}` | One JD with `structured_data` |
| `POST` | `/api/v1/alignment/generate` | Score a pair. Returns `alignment_id` |
| `GET` | `/api/v1/alignment/list` | Stored runs, newest first. `?resume_id=&jd_id=&latest_only=&skip=&limit=` |
| `GET` | `/api/v1/alignment/{id}` | One run with the full analysis |

`limit` is capped at 100; a larger value returns `422`.

## Upload dedupe

Uploads are keyed on the SHA-256 of the file bytes, stored in `resumes.content_hash`.
Re-uploading identical content returns the **existing record** — no second file on disk and no
repeated parse:

```
POST /resume/upload   (same bytes, second time)
-> 200 OK, the same resume id
   { "duplicate_of_existing": true, ... }
```

This mattered concretely: `backend/uploads/` had accumulated 14 PDFs for only 2 distinct
resumes. Existing files were deliberately left in place — some are referenced by resume rows
already in the database.

The hash lookup is scoped to the owner and runs **before** parsing, so a duplicate upload costs
one indexed query.

## Alignment history

Every `generate` appends a row rather than overwriting. Score movement over time stays
recoverable, which is what the dashboard and resume-versions views need.

```
GET /alignment/list?resume_id=...&jd_id=...
[
  { "id": "...", "alignment_score": 78.2, "created_at": "2026-08-11T..." },
  { "id": "...", "alignment_score": 66.7, "created_at": "2026-08-09T..." }
]

GET /alignment/list?resume_id=...&jd_id=...&latest_only=true
-> just the newest run per resume/JD pair
```

`latest_only` uses Postgres `DISTINCT ON (resume_id, jd_id)`, which requires those columns to
lead the `ORDER BY`; the newest-first sort is applied to the deduplicated set afterwards.

## List vs detail

List rows carry **scores only**, so a long history stays cheap to fetch:

```json
{ "id", "resume_id", "jd_id", "alignment_score", "ats_score",
  "skill_match_score", "experience_match_score", "created_at" }
```

`GET /alignment/{id}` adds the full analysis from `alignment_scores.analysis_data`:
`breakdown`, `component_weights`, `matched_skills`, `partial_skills`, `missing_skills`,
`ats_breakdown`, `ats_warnings`, `feedback`, `improvement_suggestions`, `extraction_health`.

### Column vs field name

The database column is `total_alignment_score`; the API field is `alignment_score`, matching the
generate response. The mapping lives in `_to_summary`.

## Stale schema handling

`structured_data` carries a `schema_version`, but until now nothing checked it on read. A resume
stored before Phase 2 kept `experience` as a list of **strings**, and the Phase 4 scorer — which
expects objects — crashed with `AttributeError: 'str' object has no attribute 'get'` as soon as
dedupe returned one of those old rows.

Two defences now exist:

1. **The scorer re-parses stale payloads.** `is_current_schema` / `is_current_jd_schema` gate the
   stored blob; anything older is re-parsed from `raw_text` and written back. Trusting a payload
   whose field shapes differ would score it wrongly even if it did not crash.
2. **Readers tolerate any shape.** `schemas.structured.entries(payload, key)` returns only the
   mapping entries of a list field, so a legacy record degrades to a lower score rather than a
   500. Used by the alignment components and the ATS engine.

This is the general rule for anything consuming `structured_data`: check the version, or read it
through `entries()`.

## Repositories

- `ResumeRepository.get_by_content_hash(owner_id, content_hash)` — the dedupe lookup
- `AlignmentRepository.list_alignments(...)` — filtering, `latest_only`, pagination
- `AlignmentRepository.get_latest_for_pair(resume_id, jd_id)` — most recent run for a pair

All reads exclude soft-deleted rows (`is_deleted == False`), inherited from `BaseRepository`.

## Tests

`backend/tests/test_alignment_readback.py` covers the summary/detail mappers (including the
column rename, null scores, and rows with missing or partial `analysis_data`) and the dedupe
branch — asserting a duplicate upload never re-parses, never writes a file, and looks up by the
SHA-256 of the bytes.

`backend/tests/test_scoring.py::TestStalePayloads` is the regression guard for the legacy-shape
crash.

```bash
cd backend && ../.venv/bin/python -m pytest tests -q
```

## Known limitations

- No delete endpoints; `BaseRepository.remove` supports soft delete but nothing exposes it.
- Ownership is still the demo user, so list endpoints are not scoped per real user.
- `GET /alignment/list` returns a bare array with no total count; pagination is `skip`/`limit`
  only.
- The 12 redundant files already in `uploads/` were left untouched by decision.
