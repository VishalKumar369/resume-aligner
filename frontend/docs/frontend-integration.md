# Frontend integration

> Delivered in Phase 8. Before this, 12 hardcoded data arrays across 10 files drove every
> dashboard tile, chart, table, and the entire learning page. Only login, signup, and upload
> called the API at all.

## Structure

```
frontend/
├── services/api.ts            all endpoints + auth interceptors + error helper
├── hooks/useApi.ts            fetch-on-mount with loading / error / reload
├── components/ui/States.tsx   Skeleton, ErrorState, EmptyState, ScorePill, PriorityBadge
├── components/upload/ExtractionReview.tsx
├── components/dashboard/      CareerRadarChart, SkillHeatmap, CompanyTrackerTable
└── app/                       pages, all data-driven
```

## Auth is now real

Login used to be decorative: the backend accepted a JWT and then served every request from a
single shared demo user, so two accounts saw each other's resumes.

`get_current_user` now resolves the token to a real user and every data route is scoped to it.
Alignments and resume versions carry no owner column, so they are constrained through the resume
that produced them.

| Request | Result |
|---|---|
| No token | `401` |
| Another user's resume, JD, alignment, version, or company | `404` |
| Own data | served |

A cross-account `404` rather than `403` is deliberate: a `403` would confirm the record exists.

`api.ts` clears the stored token on any `401`, so an expired session sends the user to login
instead of looping.

## Every page reads real data

| Page | Source |
|---|---|
| `/upload` | resume upload → JD upload → alignment → optimize → dashboard summary |
| `/dashboard` | `/dashboard/summary` + latest alignment detail for the radar |
| `/dashboard/skills` | `skill_gap_detail`, `partial_skills` |
| `/dashboard/readiness` | readiness, trend, latest breakdown |
| `/dashboard/resume-versions` | real versions with working `.docx` / PDF downloads |
| `/learning` | `/learning/roadmap` |
| `/company/[id]` | `/company/{id}/insights` |

Every page handles three states: loading skeleton, error with retry, and an empty state driven by
the backend's `has_data` flag — a new account sees an invitation to analyze something rather than
a grid of zeros.

## The extraction review panel

The original complaint was *"I can't get extracted data correctly"* — and the UI gave no feedback
at all about what came out of a file. Step 1 now shows, immediately after upload:

- the parsed name, email, phone, and location
- years of experience, role count, project count
- skills grouped by the resume's own categories
- each experience entry with company and date range
- extraction method, page/word count, and confidence
- any extraction warnings, and a duplicate-upload notice

A bad parse is now visible before three more steps run on top of it, with a **Replace file**
action right there.

## Honest UI

Several places surface backend caveats rather than presenting numbers as more certain than they
are:

- **Interview signal** shows its formula and the caveat that it is a heuristic, not a model
  trained on hiring outcomes.
- **Extraction health** — when `resume_ok` is false, step 3 says the score reflects a parsing
  problem rather than a poor match.
- **Blocked rewrites** are shown with their reasons, so the user can see what the optimizer
  refused to claim on their behalf.
- **Zero deltas** read "no change — already at ceiling here" rather than implying failure.
- **The JD URL field** is labelled "saved for reference, not fetched", because URL fetching is
  not implemented.
- **Optimizer scores** carry a note explaining they are a deterministic like-for-like comparison.

## Score consistency

The optimizer's before/after pair is always scored **deterministically**, even when bullet
rewriting uses a model.

This was found during verification: the optimizer makes three model calls in quick succession,
and under free-tier rate limits one side could fall back mid-run, shifting the delta. Scoring one
side with an LLM-derived component and the other without makes the comparison meaningless.

Consequence: the optimizer's baseline can differ slightly from the alignment score shown in step
3, which may include the model-based responsibility component. The response carries
`scoring_note` explaining this, and the UI displays it.

Verified: the same stored resume and JD optimized three times produced identical numbers
(`baseline align 32.0 ats 52.5 → align 32.0 ats 52.5`, three times).

## Running it

```bash
# backend
cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000 --reload

# frontend
cd frontend && npm run dev
```

`NEXT_PUBLIC_API_URL` in `frontend/.env.local` must point at the backend (default
`http://localhost:8000`). Sign up first — every data endpoint requires a token now.

## Checks

```bash
cd frontend && npx tsc --noEmit    # types
cd frontend && npm run build       # full build, 13 routes
cd backend && ../.venv/bin/python -m pytest tests -q
```

## Known limitations

- Roadmap module completion is tracked in browser state only; nothing is persisted.
- `/dashboard/resume-versions` shows versions for the most recent resume, with no resume picker.
- No delete or rename actions anywhere.
- The settings page is still static.
- Existing rows created before per-user scoping belong to the old demo user and are no longer
  reachable from any account.
