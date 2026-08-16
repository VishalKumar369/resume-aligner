# Documentation index

Every document is tagged so you can tell **what the system does** from **what it was originally
designed to do**. Where the two differ, the design document says why.

| Tag | Meaning |
|---|---|
| **As built** | Describes the code as it is. Trust these first |
| **Design intent** | Written before implementation. Header states how far it was followed |
| **Not built** | Kept as forward-looking design; none of it exists yet |
| **Retired** | Superseded; the file points at what replaced it |

---

## Start here

| Document | |
|---|---|
| [../README.md](../README.md) | What the project is |
| [getting-started.md](getting-started.md) | **As built** — run it locally, first-run walkthrough, troubleshooting |
| [backend-analysis-and-redesign-plan.md](backend-analysis-and-redesign-plan.md) | **As built** — the original analysis of what was broken, and the phase-by-phase record of what was fixed |

## Reference

| Document | |
|---|---|
| [api-design.md](api-design.md) | **As built** — all 20 endpoints, auth model, status codes, response shapes |
| [database-schema.md](database-schema.md) | **As built** — all 9 tables, real columns, ownership paths, migrations |

## How it works

Ordered as data flows through the system.

| Document | |
|---|---|
| [../backend/docs/extraction-pipeline.md](../backend/docs/extraction-pipeline.md) | File → text. Magic-byte detection, PDF/DOCX extraction, cleaning, quality scoring |
| [../backend/docs/structured-extraction.md](../backend/docs/structured-extraction.md) | Resume text → validated JSON. Sections, dates, skills, the heuristic and LLM extractors |
| [../backend/docs/jd-extraction.md](../backend/docs/jd-extraction.md) | Job posting → validated JSON. Mandatory vs preferred, seniority, experience ranges |
| [../backend/docs/scoring-engine.md](../backend/docs/scoring-engine.md) | Alignment and ATS scoring. Weighted skill matching, partial credit, gap ranking |
| [../backend/docs/optimization-engine.md](../backend/docs/optimization-engine.md) | Tailoring a resume. The anti-fabrication guard, document export |
| [../backend/docs/analytics-and-learning.md](../backend/docs/analytics-and-learning.md) | Dashboard, commonality gaps, learning roadmap, company insights |
| [../backend/docs/persistence-and-readback.md](../backend/docs/persistence-and-readback.md) | What is stored, alignment history, dedupe, stale-schema handling |
| [../backend/docs/llm-budget.md](../backend/docs/llm-budget.md) | Per-feature LLM switches, caching, quota handling |
| [../frontend/docs/frontend-integration.md](../frontend/docs/frontend-integration.md) | How each page is wired, auth, loading/empty/error states |

## Planned

| Document | |
|---|---|
| [../backend/docs/ocr-implementation-plan.md](../backend/docs/ocr-implementation-plan.md) | OCR for scanned PDFs — the step-by-step plan, not yet built |

## Design intent

Written before the build. Each header records what was followed and what changed.

| Document | Status |
|---|---|
| [architecture.md](architecture.md) | Partly built — no Redis, Celery, or worker cluster |
| [system-flow.md](system-flow.md) | Built — but synchronous, with no task queue |
| [resume-parser.md](resume-parser.md) | Built — different PDF libraries; OCR stubbed |
| [jd-parser.md](jd-parser.md) | Built |
| [alignment-engine.md](alignment-engine.md) | Built — no embeddings; weights redistributed |
| [ats-scoring-engine.md](ats-scoring-engine.md) | Built — deterministic rather than LLM-based |
| [skill-gap-engine.md](skill-gap-engine.md) | Built — no market-demand index |
| [learning-roadmap-engine.md](learning-roadmap-engine.md) | Built — official docs instead of course APIs |
| [resume-optimizer.md](resume-optimizer.md) | Built — anti-fabrication enforced mechanically |
| [resume-versioning.md](resume-versioning.md) | Built — local disk, no rollback |
| [dashboard-analytics.md](dashboard-analytics.md) | Built — interview probability is a stated heuristic, not a model |
| [company-intelligence-engine.md](company-intelligence-engine.md) | Built differently — only from the user's own postings |
| [security.md](security.md) | Partly built — JWT and scoping yes; no RBAC, scanning, or PII masking |
| [development-roadmap.md](development-roadmap.md) | Superseded by the phase plan |

## Not built

| Document | |
|---|---|
| [embeddings-pipeline.md](embeddings-pipeline.md) | No embeddings, no `pgvector`. Semantic matching is approximated deterministically |
| [scaling-strategy.md](scaling-strategy.md) | No queues, workers, or horizontal scaling |
| [deployment-architecture.md](deployment-architecture.md) | No Dockerfile, compose, K8s manifests, or CI |

## Retired

| Document | Replaced by |
|---|---|
| [analysis-feature-implementation.md](analysis-feature-implementation.md) | The phase plan and the extraction docs |
| [frontend-backend-integration-plan.md](frontend-backend-integration-plan.md) | `frontend-integration.md` and `api-design.md` |
| [../backend/docs/analysis-workflow.md](../backend/docs/analysis-workflow.md) | The four pipeline docs above |
| [../backend/docs/analysis-persistence.md](../backend/docs/analysis-persistence.md) | `persistence-and-readback.md` |

---

## Things worth knowing

Decisions that surprise people reading the code for the first time:

- **No embeddings.** `pgvector` is in `requirements.txt` but unused. Skill matching uses a
  canonical vocabulary with aliases; responsibility overlap uses content words.
- **The LLM is optional and mostly off.** Extraction and scoring are deterministic and
  reproducible. Only bullet rewriting uses a model by default, because free quotas are metered
  per day.
- **Nothing is invented.** The optimizer diffs every rewrite against its original and discards
  any that adds a figure, technology, or name. Company insights report only what the user's own
  postings say. Interview probability states that it is a heuristic.
- **A failed parse is never scored as a weak candidate.** `extraction_health` on every alignment
  distinguishes the two.
- **Cross-account reads return 404, not 403** — a 403 would confirm the record exists.
- **Soft delete everywhere.** Every read filters `is_deleted`; nothing is removed.
