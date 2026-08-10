# Scoring engine

> Delivered in Phase 4. Implements docs/alignment-engine.md and
> docs/ats-scoring-engine.md. Phases 2 and 3 made the inputs correct; this makes the
> scoring use them.

## Where it lives

```
backend/app/services/alignment/
├── skill_matcher.py    weighted skill matching, partial credit, P1/P2/P3 gaps
├── components.py       responsibility overlap, project relevance, seniority
├── llm_enhancer.py     optional LLM pass (responsibility + prose only)
├── scorer.py           combines components, renormalises, builds the response
└── persistence.py      stores the full breakdown

backend/app/services/ats/
├── ats_engine.py       deterministic 5-component ATS score
└── ats_scorer.py       entry point; optional LLM feedback enrichment
```

## What was wrong

`ats_score` was literally `min(100, alignment_score + 3)` — not an ATS evaluation, just the
alignment score nudged upward. `ATSScorerService` existed but was called from nowhere.

Meanwhile `preferred_skills`, `responsibilities`, `qualifications`, `projects[].tech_stack` and
`seniority` were all parsed by Phases 2–3 and **entirely unused**. Every mandatory skill counted
equally, so missing `Kubernetes` cost exactly as much as missing `Git`, and a resume with Docker
scored zero against a Kubernetes requirement.

## Alignment score

Weights follow `docs/alignment-engine.md`. Tool match is folded into skills because there is no
separate data source for it.

| Component | Weight | Computed from |
|---|---|---|
| `skill_match` | 0.40 | weighted mandatory coverage + preferred bonus |
| `responsibility_match` | 0.20 | JD responsibility vocabulary echoed by resume experience |
| `project_match` | 0.20 | JD skills demonstrated in `projects[].tech_stack` / highlights |
| `seniority_match` | 0.20 | resume years vs `min_experience_years`, else seniority bands |

### Renormalisation

**A component with no data is dropped, and the remaining weights renormalise.** A missing input
is not the same as a bad score: a senior candidate with no projects section would otherwise be
punished for a section they deliberately omitted.

```
full data:        skills .40 + responsibilities .20 + projects .20 + seniority .20
no projects:      skills .50 + responsibilities .25 + seniority .25
```

`component_weights` in the response always reports the weights actually used, and always sums
to 1.

## Skill matching

Three rules replace plain set intersection:

**Importance weighting.** Base weight 1.0; `+0.5` if the skill is named in the job title, or
`+0.25` if repeated three or more times across the posting.

**Preferred skills add, never subtract.** They are not part of the mandatory denominator; full
coverage of them is worth up to `+5` points on top. Missing every nice-to-have costs nothing.

**Partial credit.** A requirement whose *category* the resume covers with a different tool earns
`0.4` credit and is reported under `partial_skills` rather than `missing_skills`.

```
JD wants Kubernetes (category: containers)
resume has Docker   (category: containers)
  -> 0.4 credit, partial_skills: [{skill: "Kubernetes", covered_by: "Docker"}]
```

Categories live in `skill_vocabulary.SKILL_CATEGORIES`. `PARTIAL_CREDIT_CATEGORIES` controls
where substitution is credible — **`language` is deliberately excluded**, because knowing Java
says little about a Python role.

### Gap priority

Per `docs/skill-gap-engine.md`:

| Priority | Meaning |
|---|---|
| **P1** | missing mandatory skill with above-base weight (in the title, or heavily repeated) |
| **P2** | any other missing mandatory skill |
| **P3** | missing preferred skill |

`missing_keywords` keeps its original flat shape for the existing UI, but now returns **display
names** (`Kubernetes`) rather than the lowercase canonical forms (`kubernetes`) it used to.

## ATS score

Implements `docs/ats-scoring-engine.md` with no LLM and no network — fully reproducible. It
measures **the resume**, not the match, so it is no longer a restatement of the alignment score.

| Component | Weight | Computed from |
|---|---|---|
| `keyword_coverage` | 0.40 | JD skills present in resume skills or raw text |
| `structural_safety` | 0.20 | `extraction_meta`: OCR use, parser fallback, text yield, page count |
| `impact_metrics` | 0.20 | share of bullets containing a number, %, or currency |
| `section_health` | 0.10 | contact, summary, experience, skills, education |
| `bullet_clarity` | 0.10 | action-verb opening and a 6–45 word window |

`structural_safety` is the component only this codebase can compute well: it reads the Phase 1
extraction record, so an image-only PDF that needed OCR is correctly flagged as unreadable by
most applicant tracking systems.

Components renormalise here too — with no JD supplied, `keyword_coverage` is dropped rather than
scored as zero.

## The LLM layer

Optional and tightly scoped. When `AIFactory.is_available()`:

- `LLMAlignmentEnhancer` may set **`responsibility_match`** and rewrite the feedback prose. That
  is the one component keyword overlap approximates badly — "owned the payments platform" and
  "led billing services end to end" are the same claim in different words.
- `ATSScorerService.compute_with_feedback` may **add feedback sentences**.

It can never move `skill_match`, `project_match`, `seniority_match`, or any ATS number. A model
outage, malformed JSON, or an out-of-range score all fall back silently to the deterministic
result, so the headline figures stay stable and reproducible.

## Response shape

Existing fields keep their meaning, so the current UI keeps working. Added:

```json
{
  "alignment_score": 68.3,
  "ats_score": 75.36,
  "breakdown": {"skill_match": 89.09, "responsibility_match": 100.0,
                "project_match": 0.0, "seniority_match": 63.33},
  "component_weights": {"skill_match": 0.4, "...": 0.2},
  "matched_skills": ["Backend", "FastAPI", "PostgreSQL", "Python"],
  "partial_skills": [{"skill": "Kubernetes", "covered_by": "Docker", "category": "containers"}],
  "missing_skills": [{"skill": "Kafka", "importance": "preferred", "priority": "P3", "weight": 0.25}],
  "ats_breakdown": {"keyword_coverage": 57.14, "structural_safety": 100.0, "...": 0},
  "ats_warnings": ["Only 33% of your bullet points contain a measurable result. ..."]
}
```

`persistence.py` stores all of it in `alignment_scores.analysis_data`, so the dashboard,
skill-gap, and learning-roadmap features can build on it without re-scoring.

## Discrimination check

Same resume, two postings:

| | Relevant backend role | Principal SRE role |
|---|---|---|
| `alignment_score` | **72.31** | **10.97** |
| `skill_match` | 90.77 | 10.00 |
| `responsibility_match` | 100.0 | 15.87 |
| `seniority_match` | 63.33 | 19.00 |

## Tests

`backend/tests/test_scoring.py` covers skill weighting, partial credit (and its deliberate
absence across languages), P1/P2/P3 ranking, the preferred-never-subtracts rule, each ATS
component, renormalisation on dropped components, the LLM enhancer against a fake provider, and
a regression guard asserting `ats_score` is no longer derived from `alignment_score`.

```bash
cd backend && ../.venv/bin/python -m pytest tests -q
```

## Known limitations

- `responsibility_match` is content-word overlap, not semantics, unless an API key is
  configured. Its 0.35 target ratio is a calibration guess.
- Skill-gap priority has no market-demand index; `docs/skill-gap-engine.md` describes one as a
  future addition.
- `cultural_fit_score` remains unpopulated — nothing in the data supports it.
- Embeddings and `pgvector` are still unused; cosine similarity over `text-embedding-3-*` would
  replace the responsibility heuristic.
