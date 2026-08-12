# LLM budget, caching, and quota handling

> Added after Phase 8, in response to a concrete finding: the configured free
> tier allows **20 model calls per day**, and the app was spending 4–6 of them per
> analysis while silently changing behaviour when they ran out.

## What was found

```
Quota exceeded for metric: generate_content_free_tier_requests, limit: 20
quota_id: "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
```

Twenty requests **per day** for `gemini-2.5-flash` on this project — not per minute.

The app was calling a model in four places, so a single pass through the flow cost:

| Step | Calls |
|---|---|
| Resume upload (extraction) | 1–2 (retry on bad JSON) |
| JD upload (extraction) | 1–2 |
| Alignment (responsibility component) | 1 |
| Optimize (bullet rewriting) | 1 |

About **four complete runs per day**, after which every feature quietly fell back to its
deterministic path. Results appeared to change between sessions for no visible reason.

### A correction

An earlier note in the phase plan claimed LLM resume extraction "produces worse data than the
heuristic", citing an alignment of 32.0 against 68.3. Only the 68.3 run's extractor was actually
confirmed (it had `fallback_used: true`). The 32.0 run was **never verified** to have used the
LLM, and the difference is at least as likely to have come from the JD parsing differently. That
claim was not supported by the evidence and has been withdrawn.

What is measured: the heuristic extractor parses this project's resumes at confidence `1.0`, with
correct companies, correct date ranges, correct durations, and 45 skills.

## Where the budget goes

Per-feature switches in `app/core/config.py`:

```python
LLM_FOR_RESUME_EXTRACTION = False
LLM_FOR_JD_EXTRACTION     = False
LLM_FOR_ALIGNMENT         = False
LLM_FOR_BULLET_REWRITING  = True
```

Rewriting prose is the one thing a rule genuinely cannot do. Extraction and scoring have strong
deterministic implementations, so spending a daily-metered call on them is poor value — and it
also makes scores non-reproducible.

Result: a full flow costs **1 call instead of 4–6**, and every score is reproducible.

`AIFactory.is_available(feature)` checks the key, the feature switch, and the cooldown together.
`AIFactory.unavailable_reason(feature)` returns a user-facing explanation, which the extractors
record as `extraction_meta.llm_skipped_reason`.

## Caching

`app/services/ai/cache.py` stores model results in the `llm_cache` table, keyed by a SHA-256 of
the feature plus its exact inputs. Database-backed rather than in-memory, because a restart
should not discard the day's budget.

The bullet-rewrite key covers the role, the mandatory skills, the responsibilities, and the
bullet text. Re-optimising the same resume against the same posting is free.

**Cached payloads are the raw model response, not a verdict.** The fact guard re-runs on every
cache hit, so a change to the anti-fabrication rules applies retroactively to cached results.

Job descriptions now dedupe on a content hash the same way resumes do — pasting the same posting
twice reuses the stored parse instead of re-parsing it.

`app/utils/cache.py` was left untouched: it is unused, and its `get_cache()` returns a fresh empty
dict on every call, so it never functioned as a cache.

## Quota handling

On a failure whose text matches a quota marker (`429`, `ResourceExhausted`, `quota`,
`rate limit`, `too many requests`), `AIFactory.note_failure` starts a cooldown
(`LLM_QUOTA_COOLDOWN_SECONDS`, default 15 minutes). During it, no feature attempts a call.

This matters for latency as much as correctness. Measured on an exhausted quota:

```
optimize run 1   1.5s   attempted, rejected, fell back, reported why
optimize run 2   0.1s   cooldown active, no attempt made
```

Unrelated failures — a JSON parse error, a schema violation — do **not** trigger the cooldown;
they degrade that one call only.

The reason reaches the user rather than being swallowed: `OptimizeResponse.note` carries it and
the upload page shows it in a warning banner. `from_cache` is surfaced too, so reused results are
visible rather than looking like a fresh run.

## Turning features back on

With a paid key, flip the switches in `backend/.env`:

```bash
LLM_FOR_RESUME_EXTRACTION=true
LLM_FOR_JD_EXTRACTION=true
LLM_FOR_ALIGNMENT=true
```

Note that enabling `LLM_FOR_ALIGNMENT` makes alignment scores non-reproducible between runs, since
the responsibility component becomes model-derived. The optimizer's before/after pair stays
deterministic regardless, so its delta remains a like-for-like comparison.

## Verified behaviour

```
resume  0.2s  extractor=heuristic  "AI is disabled for resume extraction"
              name=Vishal Kumar yrs=1.9 roles=2 skills=45
jd      0.0s  extractor=heuristic
jd 2nd  0.0s  same row returned - deduped, no re-parse
align   0.0s  68.3 / ats 79.17 - deterministic
optim 1 1.5s  quota reached, reported, fell back
optim 2 0.1s  cooldown active, no call attempted
```

## Tests

`backend/tests/test_llm_budget.py` covers the switch defaults and lookup, quota-marker detection
(and that unrelated errors are ignored), cooldown gating and its message, cache key stability and
sensitivity to bullet and requirement changes, the engine writing and then reusing a cached
rewrite with only one provider call, a cache hit needing no provider at all, and cached payloads
being re-verified by the fact guard.

## Known limitations

- The cooldown is per-process; multiple workers each discover the quota separately.
- Cache entries never expire, so a prompt change requires clearing `llm_cache` to take effect on
  previously-seen inputs.
- There is no counter of calls remaining today — the quota is only discovered by being refused.
