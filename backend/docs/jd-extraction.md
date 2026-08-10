# Job description extraction

> Delivered in Phase 3. Gives the JD side the same treatment the resume side got in Phase 2,
> so alignment compares two known shapes instead of two bags of keywords.

## Where it lives

```
backend/app/schemas/jd_structured.py               the contract (JDStructuredData)
backend/app/services/parsing/
├── section_utils.py            generic labelled-section splitting (shared with resumes)
├── jd_sections.py              ABOUT / REQUIREMENTS / PREFERRED / RESPONSIBILITIES / BENEFITS
├── heuristic_jd_extractor.py   deterministic extractor (always available)
├── llm_jd_extractor.py         LLM extractor (only with an API key)
├── jd_extractor_selector.py    picks one, falls back on any failure
└── jd_parser.py                the front door used by routes and the scorer
```

## Entry point

```python
from app.services.parsing.jd_parser import JDParserService

data = await JDParserService().parse(raw_text)          # dict
model = await JDParserService().parse_to_model(raw_text)  # Pydantic object
```

## The problem this solves

The previous keyword parser scanned the entire posting with one skill list. On a normal JD that
produced:

```json
"company": "",                                ← only matched a literal "Company:" prefix
"preferred": ["nice to have"],                ← the cue phrase itself, not a skill
"mandatory": ["Backend", "FastAPI", "Kafka",  ← Kafka/Kubernetes/Terraform are nice-to-haves;
   "Kubernetes", "PostgreSQL", "Python",         "Backend" came from the job title
   "Redis", "Terraform"],
"responsibilities": ["<the entire JD as one blob>"]
```

Two of those actively distorted scoring: optional skills counted as mandatory, so candidates
were penalised for skills the posting never demanded; and words from the title were reported
as missing skills.

## Flow

```
raw JD text
   │
   ▼
split_jd_sections()      header / about / requirements / preferred / responsibilities / benefits
   │
   ▼
selector: LLM available?
   ├── yes ──► LLMJDExtractor ──(any failure)──┐
   └── no  ───────────────────────────────────┤
                                              ▼
                                   HeuristicJDExtractor
   │
   ▼
JDStructuredData  (Pydantic-validated, schema_version tagged)
```

## The contract

```json
{
  "schema_version": "1.0",
  "role": "Senior Backend Engineer",
  "company": "Acme Technologies",
  "location": "Bengaluru, India",
  "work_mode": "hybrid",
  "employment_type": "Full-Time",
  "seniority": "senior",
  "min_experience_years": 5,
  "max_experience_years": null,
  "requirements": {
    "mandatory_skills": ["Python", "FastAPI", "PostgreSQL", "Redis"],
    "preferred_skills": ["Kubernetes", "Terraform", "Kafka"],
    "normalized_mandatory": ["python", "fastapi", "postgresql", "redis"],
    "normalized_preferred": ["kubernetes", "terraform", "kafka"],
    "qualifications": ["Bachelor's degree in Computer Science or equivalent"]
  },
  "responsibilities": ["Design and own backend services end to end", "Mentor junior engineers"],
  "keywords": ["Python", "FastAPI", "..."],
  "extraction_meta": {
    "extractor": "heuristic", "confidence": 1.0,
    "skills_scoped_to_sections": true,
    "sections_found": ["about", "requirements", "preferred", "responsibilities"]
  }
}
```

## Skill scoping

Skills are read from the sections that actually state requirements — never from the title or
company boilerplate.

| Section | Feeds |
|---|---|
| Requirements / Qualifications / What we're looking for | `mandatory_skills` |
| Nice to have / Preferred / Bonus | `preferred_skills` |
| Responsibilities / About / Benefits | nothing |
| Title and header block | nothing |

A skill stated as required stays required even if the posting repeats it under "nice to have".

**Unstructured postings.** When no section headers are recognised, the body (everything after
the first line) is scanned instead, and skills sitting on a "nice to have" / "bonus" /
"preferred" line are demoted. There the cue line is the only signal available, so it wins over
the untargeted scan. `extraction_meta.skills_scoped_to_sections` records which mode ran.

## Header parsing

`Acme Technologies - Bengaluru, India (Hybrid)` yields company, location, and work mode.
Identity fields are only read from the header block, and only from lines that look like a
**label rather than a sentence** (≤10 words, no trailing period). A posting written entirely as
prose returns `role: null` and `company: null` — guessing would be worse than admitting nothing
was found.

## Experience years

`5+ years`, `3-5 years`, `at least 4 years`, `2 to 4 yrs` are all parsed into
`min_experience_years` / `max_experience_years`. The unit is mandatory, so counts like
`20+ REST APIs` are never mistaken for experience. Requirements sections are checked before the
rest of the posting.

`seniority` comes from title/body terms (`senior`, `staff`, `principal`, `lead`, `intern`,
`junior`), falling back to a band derived from `min_experience_years`.

## Title and company on the JD record

The upload page currently sends `title: "Target Role"` and `company_name: "Company"` for every
JD. `jd_routes` treats known placeholders as "nothing supplied" and stores the parsed role and
company instead, so the JD list shows real values before the frontend is fixed in Phase 8. A
genuine client-supplied title always wins.

An upload with no `raw_text` is now rejected with `422` rather than persisting an empty JD.

## Effect on alignment

`scorer.py` matches against `normalized_mandatory` and reads `min_experience_years`, with
fallbacks to the pre-Phase-3 keys so older rows still score. Preferred skills are **not** counted
as requirements, so `missing_keywords` lists only genuine must-haves.

## The LLM extractor

Same rules as the resume side: activates only when `AIFactory.is_available()`, `temperature=0.0`,
JSON-only prompt, recovers JSON from fences or prose, one repair retry, schema-validated, and
raises `LLMJDExtractionError` so the selector falls back. Its prompt explicitly forbids treating
a word from the job title or company boilerplate as a skill.

## Tests

`backend/tests/test_jd_extraction.py` covers section detection (including
`Preferred Qualifications` beating `Qualifications`), mandatory/preferred separation, title-word
exclusion, unstructured fallback with cue-word demotion, experience-range parsing, the
`20+ REST APIs` false positive, prose-not-a-title handling, the LLM path against a fake provider,
and selector fallback.

```bash
cd backend && ../.venv/bin/python -m pytest tests -q
```

## Known limitations

- JD URL fetching is not implemented; the UI's URL field is still unused (deferred by decision).
- `qualifications` only captures lines containing a degree term.
- Salary and benefits are parsed into no fields yet.
- Scoring still treats every mandatory skill as equally weighted, and `ats_score` is still
  `alignment + 3` — both are Phase 4.
