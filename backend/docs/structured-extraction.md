# Structured resume extraction

> Delivered in Phase 2. This is the layer that turns extracted **text** into validated
> **structured JSON**. Phase 1 fixed reading the file; this fixes understanding it.

## Where it lives

```
backend/app/schemas/structured.py                  the contract (ResumeStructuredData)
backend/app/services/parsing/
├── sections.py                    splits text into SUMMARY / EXPERIENCE / SKILLS / ...
├── date_utils.py                  parses date ranges, merges overlaps
├── line_utils.py                  rejoins wrapped lines, bracket-safe splitting
├── skill_vocabulary.py            canonical skills + aliases + soft skills
├── heuristic_resume_extractor.py  deterministic extractor (always available)
├── llm_resume_extractor.py        LLM extractor (only with an API key)
├── extractor_selector.py          picks one, falls back on any failure
└── resume_parser.py               the front door used by routes and the scorer
```

## Entry point

```python
from app.services.parsing.resume_parser import ResumeParserService

parser = ResumeParserService()
data = await parser.parse(text)             # dict, matches ResumeStructuredData
model = await parser.parse_to_model(text)   # the Pydantic object
```

## Flow

```
clean text
   │
   ▼
split_sections()          header / summary / experience / education / skills / projects / ...
   │
   ▼
selector: LLM available?
   ├── yes ──► LLMResumeExtractor ──(any failure)──┐
   └── no  ─────────────────────────────────────┐  │
                                                ▼  ▼
                                     HeuristicResumeExtractor
   │
   ▼
ResumeStructuredData  (Pydantic-validated, schema_version tagged)
```

The LLM is never load-bearing. A missing key, a network error, malformed JSON, or a schema
violation all degrade to the heuristic extractor — the upload never fails because of the LLM.

## The contract

`structured_data` always matches `ResumeStructuredData` and carries `schema_version`.
Consumers should check it with `is_current_schema(payload)` and treat anything else as stale.

```json
{
  "schema_version": "1.0",
  "personal_info": {
    "name": "Vishal Kumar", "title": null,
    "email": "...", "phone": "+91 9148774048", "location": null,
    "links": {"linkedin": "...", "github": "...", "portfolio": null, "other": []}
  },
  "summary": "AI/ML-focused Software Engineer ...",
  "skills": {
    "hard_skills": ["Python", "FastAPI", "AWS (EC2, S3)", ...],
    "soft_skills": ["Teamwork"],
    "normalized": ["python", "fastapi", "aws", "rag", ...],
    "categories": {"Languages": ["Python", "TypeScript"], "Databases": [...]}
  },
  "experience": [{
    "company": "The Math Company (MathCo)",
    "role": "Associate Software Engineer, R&D",
    "location": "Bengaluru, Karnataka",
    "start_date": "2025-02", "end_date": "present",
    "duration_months": 19, "is_current": true, "is_internship": false,
    "highlights": ["Built an AI-powered ...", "..."]
  }],
  "education": [{
    "degree": "B.Tech in Computer Science",
    "institution": "Indian Institute of Information Technology, Dharwad",
    "location": "Dharwad, Karnataka",
    "start_year": 2021, "end_year": 2025, "score": null, "highlights": [...]
  }],
  "projects": [{"name": "MediQuizz", "tech_stack": ["React.js", ...], "highlights": [...]}],
  "certifications": [{"name": "...", "issuer": "AWS", "year": 2023}],
  "achievements": ["Solved 500+ DSA problems ..."],
  "total_experience_years": 1.9,
  "extraction_meta": {"extractor": "heuristic", "confidence": 1.0, "fallback_used": false}
}
```

## How the heuristic extractor works

**Sections.** A line is a header when it stands alone and matches a known alias. `SKILLS` is a
header; `Languages: Python, SQL` is not, because content follows the colon.

**Wrapped lines.** A PDF breaks lines at the page margin, not at sentence ends. A line
continues the one above when the previous line stopped without terminal punctuation and the
current line does not start a bullet, a `Category:` line, or a dated header.

**Entries.** Each experience/education/project entry is anchored on its **date range**. The
dated line gives the role (or degree); the line above gives the company (or institution).

```
Globex Analytics    Bengaluru, Karnataka     <- company + location
Senior Data Engineer   March 2022 - Present  <- role + dates   (the anchor)
- highlight
```

**Locations.** Split points are scanned right to left, taking the first that parses, so
`Acme Tech Bengaluru, Karnataka` keeps `Acme Tech`. A short prefix list (`San`, `New`, `Los`, …)
keeps two-word cities such as `San Francisco, CA` intact.

**Skills.** `Category: a, b, c` lines are parsed directly, with bracket-safe splitting so
`AWS (EMR, S3)` survives as one skill. The result is the union of what the resume lists and
what the canonical vocabulary recognises anywhere in the text. `normalized` strips
parentheticals and maps to canonical forms, so a JD asking for `React` matches a resume
listing `React.js`.

**Experience totals.** Date ranges are merged before summing, so concurrent roles are not
double-counted and consecutive ones form a single stretch.

## Skill normalization

| Resume writes | `normalized` | Why it matters |
|---|---|---|
| `React.js` | `react` | JD asking for "React" now matches |
| `AWS (EC2, S3)` | `aws` | parentheticals removed |
| `RAG (Retrieval-Augmented Generation) Pipelines` | `rag` | unambiguous vocabulary hit |
| `k8s` | `kubernetes` | alias resolution |
| `Postgres` | `postgresql` | alias resolution |

The alignment scorer matches on `normalized`, falling back to `hard_skills`.

## Soft skills

Previously every resume received the same three soft skills regardless of content. They are now
detected from a vocabulary and returned **only when actually mentioned** — an empty list is a
valid, honest answer.

## The LLM extractor

Activates only when `AIFactory.is_available()` is true (a real key for the configured provider).

- `temperature=0.0`, JSON-only system prompt with an explicit schema block
- Recovers JSON from markdown fences or surrounding prose
- One repair retry when the response is not parseable
- Validated against `ResumeStructuredData`; failure raises `LLMExtractionError`
- **Durations and totals are computed in Python**, never taken from the model — arithmetic is
  not something to trust an LLM with
- Input truncated to 12,000 characters for free-tier context limits

### Enabling it

1. Get a free key: Gemini → `aistudio.google.com/apikey`, Groq → `console.groq.com/keys`
2. Set `GEMINI_API_KEY` (or `GROQ_API_KEY`) in `backend/.env`
3. Set `AI_PROVIDER` to match

No code change — the selector picks it up. `extraction_meta.extractor` will read `llm`.

## Extraction metadata

Two related records, both stored:

- `resumes.extraction_meta` — how the **file** was read (method, pages, confidence, warnings),
  with a nested `structuring` block for how the **text** was structured
- `structured_data.extraction_meta` — extractor name, confidence, sections found,
  `fallback_used` and `fallback_reason` when the LLM failed

## Tests

`backend/tests/test_structured_extraction.py` covers date maths, section detection, line
merging, every heuristic field, the LLM path against a fake provider (clean JSON, fenced JSON,
retry, schema violation), and selector fallback. It also runs the real PDFs in
`backend/uploads/` and asserts `total_experience_years > 0` — the value the old parser
always returned as `0`.

```bash
cd backend && ../.venv/bin/python -m pytest tests -q
```

## Known limitations

- A company line with **no** location whose name itself ends in `Word, Word` can be mis-split.
  The LLM extractor handles these correctly.
- Certifications are parsed from plain lines; issuers outside the known list are not detected.
- `personal_info.location` is only filled when the header block carries a `City, Region` line.
- JD parsing still uses the old keyword approach — that is Phase 3.
