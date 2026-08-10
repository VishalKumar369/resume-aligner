# Optimization engine

> Delivered in Phase 6. Step 4 of the flow ("Optimize Resume") was a `501`; it now produces a
> real tailored resume, exports it as `.docx` and PDF, and stores it as a version.

## Where it lives

```
backend/app/services/optimization/
├── fact_guard.py            rejects rewrites that invent facts
├── skill_promoter.py        surfaces evidenced-but-unlisted skills
├── reorderer.py             puts JD-relevant material first
├── bullet_advisor.py        per-bullet advice for anything not rewritten
├── llm_bullet_rewriter.py   LLM rewriting, gated by the fact guard
└── engine.py                orchestration, change log, before/after scores

backend/app/services/documents/
├── layout.py                one block list, shared by every exporter
└── writers.py               render_text / render_docx / render_pdf
```

## The rule that shapes everything

**Nothing is invented.** `resume-optimizer.md` says "Maintain 100% factual accuracy. DO NOT
fabricate experience", and that is enforced mechanically rather than left to a prompt:

- Skills are promoted **only** when already evidenced in the resume's own prose. A skill the
  JD wants but the candidate lacks stays a gap in `missing_skills`; it is never added.
- Every LLM rewrite is diffed against its original and **discarded** if it introduces a figure,
  technology, employer, or name that was not there.
- Reordering changes no text at all.

## Pipeline

```
resume + JD
   │
   ├─ score baseline (Phase 4 engines)
   │
   ▼  deep copy - the input is never mutated
promote evidenced skills
   │
   ▼
rewrite bullets (LLM)  ──►  fact guard  ──►  accepted / discarded
   │
   ▼
reorder skills, bullets, projects
   │
   ▼
advise on bullets that were not rewritten
   │
   ▼
render document, re-score against its text
   │
   ▼
OptimizationResult
```

Rewriting happens **before** reordering: a rewrite is applied by index, and reordering first
would invalidate those indices. The engine also verifies the bullet at that index still matches
the original before writing over it.

## The fact guard

`FactGuard.check(original, rewritten)` compares the two and rejects on:

| Check | Example that is rejected |
|---|---|
| New figures | original has "40 services" → rewrite says "400 services, 40% faster" |
| New technologies | rewrite adds "Kubernetes" where the original had none |
| New names / acronyms | rewrite adds "Google", or "RBAC" |
| Excessive expansion | rewrite is more than 1.8× the original word count |

Number comparison normalises separators, so rewriting `200000` as `200,000` is *not* a new fact.
The first word is exempt from the proper-noun check because sentence case capitalises it anyway.

**Verified against a live model.** On a real resume the guard blocked rewrites that would have
added "microservices" and "backend":

```
blocked: invented technologies: microservices
  would have been: "Migrated services to FastAPI ... across microservices"
```

This is deliberately conservative and will reject some benign rewrites — for a resume, that is
the right direction to err.

## What each step contributes

**Skill promotion.** A resume often proves a skill in a bullet or a project stack while the
SKILLS block never names it. Those get added under an `Additional Skills` category.
`hard_skills` and `normalized` are recomputed together so the printed section and the matching
set cannot drift.

**Reordering.** Required skills move to the front of the skills list; within each role the most
role-relevant bullet leads; projects are ranked by how many JD skills they demonstrate.
**Employment history order is never changed** — resequencing jobs would misrepresent a career.

**Bullet advice.** For every bullet not rewritten: missing metric, weak opening verb, length
outside a readable window, and which of the role's vocabulary it could mirror. This is the whole
deliverable when no model is configured.

## Document export

`layout.build_blocks()` produces one ordered block list; the text, `.docx`, and PDF writers all
render it, so the three exports cannot drift apart.

The layout is deliberately plain — single column, standard headings, real list styles, no
tables, no graphics. That is what resume parsers read reliably and what the ATS
`structural_safety` component rewards.

Tests round-trip the generated files back through the Phase 1 extraction pipeline and assert the
content is recovered with no OCR needed — the generated document is provably machine-readable.

## Before/after scoring

Baseline scores come from the original resume and its real `extraction_meta`. The optimized
scores are computed against the **rendering of the generated document**, because that is what a
screener will actually receive.

Measured on a weak resume (skills only in bullets, scanned source, bullets not leading with
verbs):

```
ATS        52.0 -> 85.0   (+33.0)
Alignment  37.5 -> 75.0   (+37.5)
promoted into printed skills: Docker, FastAPI, PostgreSQL
```

On an already-strong resume the delta is **0.0**, and that is correct rather than a failure: if
`skill_match`, `responsibility_match`, and `keyword_coverage` are already 100, the only remaining
gaps are project relevance and years of experience — neither of which can be closed honestly.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/resume/optimize` | Tailor a resume to a JD, store a version |
| `GET` | `/api/v1/resume/{id}/versions` | Versions for a resume, newest first |
| `GET` | `/api/v1/resume/versions/{id}/download?format=docx\|pdf` | Download a version |

`POST /optimize` returns the version id and number, before/after scores with deltas, the change
log (with before/after text for each rewrite), suggestions, **blocked rewrites with reasons**, and
both download URLs. `422` if the resume has no readable experience or skills; `404` if the resume
or JD is unknown.

Version numbers count from 1 per resume and are never reused, so two documents in a user's
history can never share a name.

## The LLM path

Requires a working key. When absent, the engine reports it in `note`, keeps every deterministic
improvement, and returns suggestions instead of rewrites. A provider that errors mid-run is
caught and degrades the same way.

All bullets go in **one** request (capped at 20): free-tier providers are rate limited per
minute, so batching is the difference between working and not.

### Gemini setup notes

Two things had to be fixed before any LLM feature worked:

- `google-generativeai` was pinned at `0.4.1`, which predates Gemini 1.5 GA and cannot route
  current models. Now `0.8.6`. That package line is deprecated in favour of `google-genai`;
  migrating is a future task.
- `GeminiProvider` mapped every non-`user` role to `"model"`, so system prompts were replayed as
  model turns — the model saw its own instructions as something it had already said. System
  messages now go to Gemini's `system_instruction`, `assistant` maps to `model`, and JSON-expecting
  callers pass `json_mode=True` (`response_mime_type`, or `response_format` on OpenAI/Groq).

**Model choice matters on the free tier.** `gemini-2.0-flash` returns
`Quota exceeded ... limit: 0` — no free-tier allowance — and `gemini-1.5-flash` is retired.
`gemini-2.5-flash` works and is now the default.

## Tests

`backend/tests/test_optimization.py` covers the guard (each fabrication category plus the
benign-reword and comma-formatting cases), promotion (including that an unsupported skill is
never added), reordering (including that employment order is preserved), the advisor, the
rewriter against a fake provider, engine fallback when the model is absent or dead, input
immutability, and document round-trips through the extraction pipeline.

```bash
cd backend && ../.venv/bin/python -m pytest tests -q
```

## Known limitations

- The guard is conservative: adding a category word like "backend" to a bullet counts as a new
  fact and is rejected.
- The summary is not rewritten, only bullets.
- No company-mode tailoring (`resume-optimizer.md` describes startup vs enterprise emphasis).
- Metric enhancement only advises; it never inserts placeholder numbers.
- Exports are stored on local disk via the storage adapter, not S3.
