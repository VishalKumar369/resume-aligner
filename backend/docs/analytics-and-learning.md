# Analytics, learning roadmap, and company insights

> Delivered in Phase 7 (Step 5 of the flow). `/dashboard/summary`,
> `/learning/roadmap`, and `/company/{id}/insights` all returned hardcoded values;
> every number they return now traces back to the user's own stored data.

## Where it lives

```
backend/app/services/skill_gap/
├── aggregator.py            commonality gap across every target JD
└── detector.py              single-pair gaps, now via the Phase 4 matcher

backend/app/services/dashboard/analytics.py    dashboard aggregation
backend/app/services/learning/
├── resources.py             curated official-docs library, categories, prerequisites
└── roadmap_generator.py     clustering, dependency ordering, scheduling
backend/app/services/company/insights.py       company view from the user's own JDs
```

## What was there before

| Endpoint | Before |
|---|---|
| `/dashboard/summary` | fixed `total_resumes: 5`, `avg_alignment_score: 78.4`, invented activity dated 2024, and a `dummy_user_id = uuid.uuid4()` generated per request |
| `/learning/roadmap` | four weeks of `"Mastering {skill}"` for a hardcoded skill list, with links to `https://coursera.org/...` for a course that does not exist |
| `/company/{id}/insights` | a hardcoded tech stack, culture list, and interview tips, returned for any id, naming real companies |
| `SkillGapDetectorService` | its own lowercase set difference, with `demand_index: 92` attached to every gap |

## The commonality gap

`SkillGapAggregator` reads the **stored** `analysis_data` of the newest alignment run per JD and
merges the gap lists. This reuses the weighting and P1/P2/P3 ranking Phase 4 already computed
rather than re-deriving it.

A gap's rank is `jd_count × priority_weight` (P1 = 3.0, P2 = 2.0, P3 = 0.5) — **frequency across
postings dominates**. A skill three roles demand outranks a single P1, because the common gap is
the one worth learning next. Aliases collapse first, so `k8s` and `Kubernetes` are one gap.

Only the newest run per JD counts. Re-scoring one role ten times would otherwise let it dominate
every average on the dashboard.

## Dashboard

```
GET /api/v1/dashboard/summary
```

| Field | Derivation |
|---|---|
| `totals` | row counts: resumes, JDs, alignments, optimized versions, distinct target roles |
| `avg/best_alignment_score`, `avg/best_ats_score` | over the latest run per JD |
| `career_readiness_index` | `0.65 × mean(alignment) + 0.35 × mean(ATS)` |
| `interview_probability` | band + score + **basis + caveat** (see below) |
| `top_skill_gaps`, `skill_gap_detail` | the commonality gap, with `jd_count` and priority |
| `readiness_trend` | alignment and ATS over time, oldest first so a chart reads left to right |
| `top_company_matches` | **one row per company**, its best-matching role, and `roles_tracked` |
| `recent_activity` | real `created_at` values across all four tables |
| `recommended_improvements` | top gaps, then stored ATS warnings, then partial matches |
| `has_data` | `false` before any alignment exists, so the UI shows an empty state not zeros |

Readiness weights alignment above ATS deliberately: a perfect match nobody's parser can read is
not readiness, but matching the role matters more than formatting.

### Interview probability

`dashboard-analytics.md` specifies "a logistic regression model trained on historical hiring
data". **No such model or data exists**, and inventing one would be the same failure as a
fabricated resume bullet. The endpoint instead returns a transparent heuristic that names itself:

```json
"interview_probability": {
  "band": "High",
  "score": 70.09,
  "basis": "0.6 x JD alignment + 0.4 x ATS score, averaged over your most recent run per target role",
  "caveat": "Heuristic derived from your own scores. Not a prediction model trained on hiring outcomes."
}
```

Bands: `Strong` ≥ 80, `High` ≥ 65, `Moderate` ≥ 45, `Low` below, `Unknown` with no data.

## Learning roadmap

```
GET /api/v1/learning/roadmap
```

Implements `docs/learning-roadmap-engine.md`:

1. **Clustering** — gaps group by their vocabulary category, so Docker and Kubernetes become one
   *Containerisation & Orchestration* module rather than two.
2. **Priority ordering** — modules sort by criticality, then by how many JDs demand them.
3. **Dependency ordering** — a module teaching a prerequisite is pulled ahead of the module that
   needs it. Learning Kubernetes before Docker, or FastAPI before Python, wastes the first
   module. Within a module the same rule orders the skills.
4. **Scheduling** — each module gets an ETA (2 weeks per P1/P2 skill, 1 per P3) and modules run
   back to back, producing `Week 1-2`, `Week 3`, and so on.

With no gaps it returns an empty plan and a note explaining why — not invented modules.

### Resources

Every resource is the skill's **own official documentation**: `kubernetes.io/docs`,
`docs.docker.com`, `fastapi.tiangolo.com`, `developer.hashicorp.com/terraform`. Real, free,
stable, and verifiable.

A skill with no library entry returns **no resource** rather than a plausible-looking guess. This
is a deliberate constraint: the old stub emitted truncated placeholder URLs, and an LLM asked for
course recommendations hallucinates titles and links just as readily. A test asserts no resource
URL contains `...`.

## Company insights

```
GET /api/v1/company/{companyId}/insights
```

Matches on the stored `company_name` or its slug, and reports **only** what the user's saved
postings say: roles, seniority levels, locations, work modes, employment types, the skills those
postings demand, the user's best and average alignment with them, and the gaps specific to that
company.

With no saved postings for a company it returns **404** with a message to add one. The previous
behaviour — asserting Google's tech stack, culture, and interview process from nothing — was
fabricating claims about a real organisation.

## Aggregation strategy

Everything is computed **on read**. The data volume is small, the numbers can never be stale, and
there is no cache-invalidation path to get wrong. The `DashboardSnapshot` model stays unused until
scale justifies it.

## Tests

`backend/tests/test_analytics.py` covers gap aggregation (counting, ranking, alias collapsing,
strongest-priority-wins, legacy string rows), the resource library (every URL real, unknown skills
return nothing), roadmap clustering and both levels of dependency ordering, back-to-back
scheduling, readiness and probability maths including the caveat text, latest-run-per-JD
deduplication, and the rewritten detector.

```bash
cd backend && ../.venv/bin/python -m pytest tests -q
```

## Known limitations

- No per-user scoping: ownership is still the shared demo user, so the dashboard covers
  everything stored.
- `readiness_trend` is a raw series of alignment runs, not a per-JD or rolling average.
- ETAs are fixed per priority, not calibrated against how long anything actually takes.
- `SkillGap`, `LearningPath`, and `DashboardSnapshot` tables remain unused; roadmap progress is
  tracked only in the frontend.
- The frontend dashboard and learning pages are still fully hardcoded and do not call these
  endpoints — that is Phase 8.
