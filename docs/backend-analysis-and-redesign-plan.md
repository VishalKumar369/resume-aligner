# Backend Analysis & Redesign Plan

> Status: **Phases 0–6 complete.** Phases 7–9 pending.
> Date: 2026-08-09
> Scope: the 5-step analysis flow (Upload Resume → Add JD → Review Alignment → Optimize Resume → View Analytics)
>
> Sections 2–5 describe the state **before** implementation began and are kept as the record of
> what was wrong. See §11 for what has since been fixed.

---

## 1. Executive summary

The 5-step flow is wired end-to-end in the UI, but **only steps 1 and 2 actually reach working backend code**. Step 3 fails on a request-contract mismatch, and steps 4–5 are pure frontend mock.

The reported problem — *"when I upload files I'm not able to get extracted data correctly"* — has a single, concrete root cause:

**The backend never extracts text from PDF or DOCX files. It detects that the bytes are binary and stores a placeholder sentence instead of the resume content.**

Everything downstream (skills, experience, alignment score, ATS score, missing keywords) is then computed from that placeholder sentence, which is why the extracted data looks empty or nonsensical.

A redesign of the parsing layer is required, not a patch.

---

## 2. Root cause of incorrect extraction

### 2.1 The failure path

Trace of a real PDF upload through [resume_routes.py:24-42](backend/app/api/v1/resume_routes.py#L24-L42):

```
file bytes  →  storage.upload_file()            ✅ file saved to uploads/
            →  parser._decode_text(bytes)       ❌ returns a placeholder string
            →  parser.parse_bytes(bytes)        ❌ parses that placeholder string
            →  repo.create(raw_text=..., structured_data=...)   ❌ garbage persisted
```

In [resume_parser.py:36-63](backend/app/services/parsing/resume_parser.py#L36-L63), `_looks_like_binary()` checks for the `%PDF` magic bytes and the ZIP header `PK\x03\x04` (which is what a `.docx` is). On a match, `_decode_text()` returns:

```
"[Binary or non-text content stored as file reference only for Vishal_Kumar_Resume.pdf]"
```

That literal string becomes `raw_text` in the database **and** the input to `parse()`.

### 2.2 What actually gets stored

Running the current parser against that placeholder produces:

| Field | Stored value | Expected |
|---|---|---|
| `personal_info.name` | `"[Binary or non-text content stored as..."` | `"Vishal Kumar"` |
| `personal_info.email` | `""` | real email |
| `skills.hard_skills` | `[]` | actual skills |
| `skills.soft_skills` | `["communication", "leadership", "problem solving"]` | **hardcoded constant, not extracted** |
| `experience` | `[]` | real roles |
| `education` | `[]` | real degrees |
| `experience_years` | `0` | real number |

Because `experience_years = 0` and `hard_skills = []`, the alignment scorer then yields `skill_match_score = 0`, `alignment_score ≈ 0`, and every JD keyword lands in `missing_keywords`.

### 2.3 Confirmed environment facts

- **No PDF library installed.** `requirements.txt` contains no `pypdf`, `PyMuPDF`, `pdfplumber`, or `pdfminer.six`.
- **No DOCX library installed.** No `python-docx`.
- **No OCR.** No `pytesseract` / `pdf2image` / Pillow OCR path, despite the intended pipeline calling for an OCR fallback on empty text.
- **No LLM extraction wired.** `AIFactory` exists in [factory.py](backend/app/services/ai/factory.py) but **neither `ResumeParserService` nor `JDParserService` ever calls it.**
- **No API keys configured.** `.env` has `OPENAI_API_KEY="sk-..."` (placeholder, 8 chars), `GROQ_API_KEY=""`, `GEMINI_API_KEY=""`. Any LLM call today would fail with an auth error.
- **PostgreSQL is running** and reachable on `localhost:5432`.
- **8 real PDFs already sit in `backend/uploads/`** (3 distinct files, uploaded repeatedly — no dedupe).

### 2.4 Secondary parsing defects

Even with correct text, the current parser cannot produce reliable structure:

- **Skills** are matched against a hardcoded 24-item list ([resume_parser.py:6-11](backend/app/services/parsing/resume_parser.py#L6-L11)). Anything outside that list is invisible.
- **Soft skills** are a fixed constant returned for every resume.
- **Name** is "the first non-empty line" — wrong for any resume that leads with a header, logo caption, or contact block.
- **Experience** matches any line containing `engineer|developer|manager|lead|analyst|architect` and caps at 3 entries, with `company` always `""` and `highlights` always `[]`.
- **Education** returns the generic search terms themselves (`["bachelor", "university"]`), not the actual degree, institution, or year.
- **Projects** returns "the first 3 lines with ≥3 words" — arbitrary.
- **Certifications** returns the search terms (`["aws"]`), not certification names.
- **`experience_years`** regex `(\d+)\s*\+?\s*years?` grabs the *first* number-followed-by-"years" anywhere in the document — it will happily return `2` from "2 years of college".

---

## 3. Contract mismatches (frontend ↔ backend)

These break the flow independently of parsing.

### 3.1 `POST /alignment/generate` — Step 3 is broken

[alignment_routes.py:12-16](backend/app/api/v1/alignment_routes.py#L12-L16) declares:

```python
async def generate_alignment(resume_id: uuid.UUID, jd_id: uuid.UUID, db=Depends(get_db)):
```

Bare scalar parameters in FastAPI bind as **query parameters**. The frontend sends a JSON body ([api.ts:60-61](frontend/services/api.ts#L60-L61)):

```ts
api.post("/alignment/generate", { resume_id: resumeId, jd_id: jdId })
```

Result: **HTTP 422**, and the UI shows "Alignment failed". Step 3 can never succeed as written.

### 3.2 `POST /resume/optimize` — same issue, and it is a stub

Same query-vs-body mismatch, and the handler returns a hardcoded response ([resume_routes.py:51-64](backend/app/api/v1/resume_routes.py#L51-L64)) with a fake filename and fake change list. No optimization engine exists.

### 3.3 `POST /resume/upload` — `label` silently dropped

`label: str = None` is also a query parameter, but the frontend appends it to `FormData`. It is discarded. Separately, the `resumes` table has **no `label` column**, yet `ResumeOut` exposes `label` — so it is always `null`.

### 3.4 Steps 4 and 5 never call the backend

- **Step 4 (Optimize)** in [upload/page.tsx:87-90](frontend/app/upload/page.tsx#L87-L90) just does `setCurrentStep(5)`. The "ATS Score went from 74% → 92%" text is hardcoded.
- **Step 5 (Analytics)** renders values from the step-3 response only; it never calls `/dashboard/summary`.

### 3.5 No read-back endpoints

There is no `GET /resume/{id}`, `GET /jd/{id}`, or `GET /alignment/{id}`. The frontend cannot re-fetch or display the parsed structure it just created — so the user never sees the extracted data even when it is correct.

---

## 4. Scoring engine defects

In [scorer.py](backend/app/services/alignment/scorer.py):

1. **Dead code.** Everything after the `else` block's `return` (the trailing ~25 lines) is unreachable and duplicates the live logic.
2. **Exact-string skill matching.** `resume_skills ∩ jd_skills` on capitalized tokens. No normalization, no aliasing — `"Node"` ≠ `"Node.js"`, `"K8s"` ≠ `"Kubernetes"`, `"Postgres"` ≠ `"PostgreSQL"`. Match rates are artificially low.
3. **Fabricated ATS score.** `ats_score = min(100, alignment_score + 3)`. It is not an ATS evaluation at all.
4. **`ATSScorerService` is orphaned.** The LLM-based ATS scorer in [ats_scorer.py](backend/app/services/ats/ats_scorer.py) is never called by any route.
5. **`cultural_fit_score`** column exists in the model and is never populated.
6. **Empty-input case** returns `alignment_score = 0` with no diagnostic explaining that extraction failed — indistinguishable from a genuinely bad match. This is exactly what the user is seeing.
7. **No semantic similarity.** `embeddings-pipeline.md` and `pgvector` in `requirements.txt` describe a vector path; `app/services/resume/embedding.py` is not used by the alignment flow.

---

## 5. Other findings

| # | Finding | Impact |
|---|---|---|
| 1 | **2 of 3 tests fail.** `test_analysis_workflow.py` asserts scores in `0.0–1.0` while the code returns `0–100`; the name assertion also fails. | CI signal is unreliable |
| 2 | **No upload validation.** Backend accepts any file type and any size. Frontend claims "PDF or DOCX · max 5MB" but nothing enforces it server-side. | Abuse / crash risk |
| 3 | **Auth bypassed.** Every upload calls `get_or_create_default_user()` and is attributed to `demo@resume-aligner.local`, even though JWT auth exists and the frontend sends a token. | Multi-user data is not separated |
| 4 | **No content dedupe.** Re-uploading the same file writes another copy. `uploads/` already holds 8 files for 3 distinct resumes. | Storage waste |
| 5 | **Synchronous parsing in-request.** `docs/api-design.md` specifies `202 Accepted` + `task_id`; Celery is in `requirements.txt` but no worker exists. Current behaviour blocks the HTTP request. | Timeouts on large files |
| 6 | **`structured_data` is unvalidated free-form JSON.** No Pydantic model guards the shape, so downstream features (dashboard, skill-gap, learning roadmap) cannot rely on it. | Fragile for future features |
| 7 | **Double commit.** `get_db()` commits on exit and routes also call `await db.commit()`. | Redundant, not harmful |
| 8 | **Docs claim completion that is not true.** `docs/analysis-feature-implementation.md` says the workflow "is now wired"; `frontend-backend-integration-plan.md` says the backend "now has the first analysis workflow implemented". Both overstate the current state. | Misleading |

---

## 6. Feature inventory — the 5 steps

| Step | UI | Backend endpoint | Current state | Verdict |
|---|---|---|---|---|
| 1 | Upload Resume | `POST /resume/upload` | Saves file; text extraction fails; heuristic structure | **Redesign** |
| 2 | Add Job Description | `POST /jd/upload` | Works on pasted text; keyword-list parsing only; URL field ignored | **Rework** |
| 3 | Review Alignment | `POST /alignment/generate` | **422 — request contract mismatch** | **Fix + redesign scoring** |
| 4 | Optimize Resume | `POST /resume/optimize` | Hardcoded mock; not called by UI | **Build** |
| 5 | View Analytics | `GET /dashboard/summary` | Not called by UI | **Build wiring** |

---

## 7. Target architecture

### 7.1 Intended pipeline (from your spec, made concrete)

```
Upload file
   │
   ▼
Validate  (type allowlist, size cap, magic-byte sniff)
   │
   ▼
Detect real file type  (PDF / DOCX / DOC / TXT)
   │
   ▼
Extract text  (PyMuPDF for PDF, python-docx for DOCX)
   │
   ▼
Text empty or below quality threshold?  ──yes──►  OCR fallback (pdf2image + pytesseract)
   │ no                                                    │
   ▼                                                       │
Clean & normalize  ◄─────────────────────────────────────┘
   │
   ▼
Section segmentation  (Experience / Skills / Education / Projects / Certifications)
   │
   ▼
Structured extraction
   ├── LLM extractor (primary, when a key is configured)
   └── Heuristic extractor (deterministic fallback, always available)
   │
   ▼
Validate against Pydantic schema  →  reject/repair malformed output
   │
   ▼
Persist: raw_text + structured_data + extraction metadata (method, confidence, warnings)
   │
   ▼
Compare with JD  →  alignment score + ATS score + missing skills + suggestions
```

### 7.2 Key design decisions

**Extraction must be layered, with a deterministic floor.**
LLM extraction is the quality path, but no API key is configured today. The heuristic extractor must therefore be good enough to ship on its own, and the LLM must be a drop-in upgrade behind the same interface — not a hard dependency.

**Extraction quality must be observable.**
Every parse records *how* it was extracted (`pdf_text`, `docx`, `ocr`, `llm`, `heuristic`), a confidence signal, and any warnings. When extraction fails, the API says so explicitly instead of silently returning a 0% match. This directly addresses the current "I can't tell if it's a bad resume or a broken parser" problem.

**`structured_data` gets a versioned, validated schema.**
A single Pydantic contract (`ResumeStructuredData`, `JDStructuredData`) with a `schema_version` field, so the dashboard, skill-gap, versioning, and learning-roadmap features can build on it safely.

**Skill matching moves to a normalized vocabulary.**
A canonical skill dictionary with aliases (`k8s → Kubernetes`, `postgres → PostgreSQL`, `js → JavaScript`) replaces the 24-item hardcoded list and exact string matching.

---

## 8. Proposed target JSON contracts

### 8.1 Resume `structured_data`

```json
{
  "schema_version": "1.0",
  "personal_info": {
    "name": "Vishal Kumar",
    "email": "vishal@example.com",
    "phone": "+91-XXXXXXXXXX",
    "location": "Bengaluru, India",
    "links": { "linkedin": "...", "github": "...", "portfolio": "..." }
  },
  "summary": "Full-stack engineer with 3 years ...",
  "skills": {
    "hard_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "soft_skills": ["Stakeholder communication"],
    "tools": ["Git", "Jira"],
    "normalized": ["python", "fastapi", "postgresql", "docker"]
  },
  "experience": [
    {
      "company": "MathCo",
      "role": "Software Engineer",
      "start_date": "2023-06",
      "end_date": "present",
      "duration_months": 38,
      "location": "Bengaluru",
      "highlights": ["Built ...", "Reduced ..."]
    }
  ],
  "education": [
    { "degree": "B.Tech, Computer Science", "institution": "XYZ University",
      "start_year": 2019, "end_year": 2023, "score": "8.4 CGPA" }
  ],
  "projects": [
    { "name": "Resume JD Aligner", "description": "...",
      "tech_stack": ["FastAPI", "Next.js"], "link": "..." }
  ],
  "certifications": [
    { "name": "AWS Certified Developer – Associate", "issuer": "AWS", "year": 2024 }
  ],
  "total_experience_years": 3.2,
  "extraction_meta": {
    "method": "pdf_text",
    "used_ocr": false,
    "extractor": "llm",
    "confidence": 0.91,
    "warnings": [],
    "char_count": 4820
  }
}
```

### 8.2 JD `structured_data`

```json
{
  "schema_version": "1.0",
  "role": "Senior Backend Engineer",
  "company": "Acme Tech",
  "location": "Remote",
  "employment_type": "Full-time",
  "seniority": "senior",
  "min_experience_years": 5,
  "requirements": {
    "mandatory_skills": ["Python", "Kubernetes", "PostgreSQL"],
    "preferred_skills": ["Go", "Terraform"],
    "qualifications": ["B.Tech in CS or equivalent"],
    "normalized_mandatory": ["python", "kubernetes", "postgresql"]
  },
  "responsibilities": ["Design and own backend services", "..."],
  "keywords": ["distributed systems", "microservices", "CI/CD"],
  "extraction_meta": { "extractor": "heuristic", "confidence": 0.78, "warnings": [] }
}
```

### 8.3 Alignment result

```json
{
  "alignment_id": "uuid",
  "resume_id": "uuid",
  "jd_id": "uuid",
  "alignment_score": 76.4,
  "ats_score": 68.0,
  "breakdown": {
    "skill_match": 72.0,
    "experience_match": 85.0,
    "keyword_coverage": 64.0,
    "education_match": 100.0
  },
  "matched_skills": ["Python", "PostgreSQL"],
  "missing_skills": [
    { "skill": "Kubernetes", "importance": "mandatory", "priority": "high" }
  ],
  "partial_skills": ["Docker (JD wants orchestration depth)"],
  "feedback": "Strong backend fundamentals; container orchestration is the main gap.",
  "improvement_suggestions": ["Add a Kubernetes deployment bullet to the MathCo role"],
  "extraction_health": { "resume_ok": true, "jd_ok": true, "warnings": [] }
}
```

---

## 9. Phased implementation plan

Small, independently testable increments. Each phase ends green before the next begins.

### Phase 0 — Dependencies & contract fixes *(small)*
- Add `pypdf`/`PyMuPDF`, `python-docx`, and OCR deps to `requirements.txt`; install.
- Convert `/alignment/generate` and `/resume/optimize` to Pydantic **request bodies** (fixes the 422).
- Accept `label` as a `Form` field; add the `label` column via an Alembic migration.
- Delete the unreachable dead code in `scorer.py`.
- Fix the failing tests (align the 0–100 scale).

### Phase 1 — Document text extraction layer *(the actual fix)*
- New `app/services/extraction/` package: `TextExtractor` interface + `PdfExtractor`, `DocxExtractor`, `TxtExtractor`, `OcrExtractor`.
- Magic-byte type detection (do not trust the filename or `Content-Type`).
- OCR fallback triggered when extracted text is empty or below a character/quality threshold.
- Text cleaning: de-hyphenation, ligature repair, bullet normalization, whitespace collapse, control-char stripping.
- Unit tests against the **real PDFs already in `backend/uploads/`**.

### Phase 2 — Structured resume extraction *(redesign)*
- Pydantic `ResumeStructuredData` schema (§8.1).
- Section segmenter (header detection).
- `HeuristicResumeExtractor` — proper date parsing, real company/role pairing, real education and certification entities, computed `total_experience_years` from date ranges.
- `LLMResumeExtractor` — few-shot JSON extraction via `AIFactory`, with schema validation and repair-retry.
- `ExtractorSelector` — LLM when a key is configured, heuristic otherwise; always records `extraction_meta`.

### Phase 3 — JD parsing parity
- Pydantic `JDStructuredData` schema (§8.2).
- Heuristic + LLM JD extractors behind the same interface.
- Optional: fetch and extract from the JD URL the UI already collects.

### Phase 4 — Skill vocabulary & alignment redesign
- Canonical skill dictionary with aliases and categories.
- Rewrite `AlignmentScorerService`: weighted skill / experience / keyword / education breakdown, matched vs missing vs partial, prioritized gaps.
- Wire the real `ATSScorerService` with a deterministic non-LLM fallback.
- Surface `extraction_health` so a broken parse is never reported as a 0% match.

### Phase 5 — Persistence & read-back APIs
- Store `extraction_meta`, matched/missing skills, and the full breakdown.
- Add `GET /resume/{id}`, `GET /jd/{id}`, `GET /alignment/{id}`, `GET /alignment/list`.
- Content-hash dedupe on upload.

### Phase 6 — Step 4: Optimize Resume
- `OptimizationEngine`: bullet rewriting, keyword injection, change log.
- Persist as a `ResumeVersion`; return a real download path.

### Phase 7 — Step 5: Analytics
- Implement `GET /dashboard/summary` over real persisted alignments.
- Career readiness, top skill gaps, recent activity.

### Phase 8 — Frontend integration
- Fix `api.ts` payloads to match the corrected contracts.
- Show the **extracted resume data** back to the user after step 1 (currently invisible — this is a large part of the perceived "extraction doesn't work").
- Wire steps 4 and 5 to real endpoints; remove hardcoded `74% → 92%`.
- Surface extraction warnings in the UI.

### Phase 9 — Documentation
- `backend/docs/` — extraction pipeline, schema contracts, endpoint reference, local setup.
- `frontend/docs/` — API contract, state flow, step-by-step integration map.
- Correct the existing docs that overstate current completeness.

---

## 10. Decisions (agreed 2026-08-09)

| # | Decision | Choice | Implication |
|---|---|---|---|
| 1 | **LLM provider** | **Groq / Gemini free tier** | `AI_PROVIDER` defaults to a free-tier provider. A free API key must be generated and added to `backend/.env`. Until then the heuristic extractor runs automatically, so the flow never hard-fails on a missing key. |
| 2 | **OCR** | **Deferred** | Phase 1 ships PDF + DOCX text extraction only. The OCR stage is built into the pipeline as a hook that emits an explicit `scanned_pdf_needs_ocr` warning instead of running. No system-level `tesseract` dependency for now. |
| 3 | **Parsing mode** | **Synchronous** | Parsing happens inside the upload request and the structured result is returned directly. No Celery, no polling. Revisit if OCR or large files push latency up. |
| 4 | **Auth** | **Keep demo user** | Uploads continue to attribute to `demo@resume-aligner.local`. Real JWT-scoped ownership becomes its own later phase. |

### Consequences for the phase plan
- **Phase 1** drops the OCR extractor implementation; it keeps the fallback *hook* and the warning path.
- **Phase 2** builds the heuristic extractor to production quality first (it is the guaranteed floor), then layers the LLM extractor on top via `AIFactory`.
- **Phase 0** updates Groq/Gemini model defaults to models that exist on the free tier, and adds an availability guard so a missing key degrades to heuristic parsing instead of raising an auth error.
- Auth and Celery work is explicitly **out of scope** until the analysis flow is correct end to end.

---

## 11. Implementation log

### Phase 0 — dependencies & contract fixes ✅
| Change | Where |
|---|---|
| Added `pypdf`, `pdfplumber`, `python-docx` | `requirements.txt` |
| `/alignment/generate` now takes a JSON body (**fixes the 422**) | `alignment_routes.py`, `schemas/analytics.py` |
| `/resume/optimize` takes a body and returns an honest `501` instead of a fake success | `resume_routes.py`, `schemas/resume.py` |
| `label` accepted as a `Form` field and actually stored | `resume_routes.py`, `models/resume.py` |
| Added `label`, `content_hash`, `extraction_meta` columns | migration `a1c4e7d92b30` (applied) |
| Removed ~25 lines of unreachable dead code | `alignment/scorer.py` |
| Added `extraction_health` to alignment responses | `scorer.py`, `schemas/analytics.py` |
| Free-tier model defaults (`gemini-2.0-flash`, `llama-3.3-70b-versatile`) | `config.py`, `.env`, `.env.example` |
| `AIFactory.is_available()` + `AIUnavailableError`; placeholder keys treated as absent | `ai/factory.py`, `config.py` |
| Shared skill vocabulary with aliases, replacing the duplicated 24-item list and the `.capitalize()` casing bug (`Fastapi` → `FastAPI`) | `parsing/skill_vocabulary.py` |
| Fixed the 2 failing tests and a list-indexing bug in the test helper | `tests/test_analysis_workflow.py` |

### Phase 1 — document text extraction ✅
New package `app/services/extraction/` — see [backend/docs/extraction-pipeline.md](backend/docs/extraction-pipeline.md).

- Magic-byte file type detection (does not trust filename or `Content-Type`)
- PDF via pdfplumber with a pypdf fallback; DOCX via python-docx incl. tables and headers
- Text cleaning: hyphen rejoins, bullet normalisation, ligatures, smart quotes, control chars
- Quality scoring and an honest `ExtractionResult` with `ok`, `confidence`, and `warnings`
- OCR hook in place but deliberately unimplemented (per decision 2)
- Upload validation: `400` empty, `413` over 5MB, `415` unsupported type, `422` unreadable
- The old `_looks_like_binary` / placeholder-string path is **deleted**

**Verified end to end** against a real resume PDF:

```
extraction_meta: method=pdf_text pages=1 chars=3837 words=514 confidence=1.0 warnings=[]
name  : Vishal Kumar
email : Vishal369mehta@gmail.com
skills: AWS, C++, Docker, FastAPI, Git, Java, JavaScript, LLM, Machine Learning,
        Microservices, MongoDB, MySQL, Next.js, Node.js, PostgreSQL, Python, RAG,
        REST API, React, SQL, TypeScript
```

Alignment against a sample JD returned `alignment_score 42.0`, `skill_match 60.0`,
missing `["backend", "kubernetes"]`, with `extraction_health: {resume_ok: true, jd_ok: true}`.

Test suite: **23 passed**.

### Phase 2 — structured resume extraction ✅
New contract and extractors — see [backend/docs/structured-extraction.md](backend/docs/structured-extraction.md).

| Component | File |
|---|---|
| Validated contract, `schema_version` | `app/schemas/structured.py` |
| Section segmenter | `parsing/sections.py` |
| Date-range parsing + overlap merging | `parsing/date_utils.py` |
| Wrapped-line rejoining, bracket-safe splitting | `parsing/line_utils.py` |
| Deterministic extractor | `parsing/heuristic_resume_extractor.py` |
| LLM extractor (dormant until a key is set) | `parsing/llm_resume_extractor.py` |
| Selection + guaranteed fallback | `parsing/extractor_selector.py` |
| Soft-skill vocabulary; `js` alias no longer fires inside `Express.js` | `parsing/skill_vocabulary.py` |
| Scorer reads `total_experience_years`, matches on canonical skills | `alignment/scorer.py` |

**Before → after on the same real PDF:**

| Field | Phase 1 | Phase 2 |
|---|---|---|
| `total_experience_years` | `0` | `1.9` (merged date ranges) |
| `experience[].company` | `""` | `The Math Company (MathCo)`, `DataAstraa` |
| `experience[].dates` | absent | `2025-02 → present` (19mo), `2024-05 → 2024-08` (4mo) |
| `experience[].highlights` | `[]` | all bullets, unwrapped |
| `education` | `["bachelor", "university"]` | `B.Tech in Computer Science` @ `Indian Institute of Information Technology, Dharwad` (2021–2025) |
| `soft_skills` | hardcoded 3 for everyone | detected only when mentioned |
| `skills.categories` | absent | 6 real categories from the resume |
| `projects` | 3 arbitrary lines | 3 real projects with tech stacks |

**Effect on alignment** (same resume + JD, before vs after):

```
experience_match_score:   0.00  ->  95.00     (real experience total)
skill_match_score:       60.00  ->  66.67     ("React" now matches "React.js")
alignment_score:         42.00  ->  75.17
```

Test suite: **62 passed** (was 23).

### Phase 3 — JD parsing parity ✅
JD side brought up to the same standard — see [backend/docs/jd-extraction.md](backend/docs/jd-extraction.md).

| Component | File |
|---|---|
| Validated JD contract, `schema_version` | `app/schemas/jd_structured.py` |
| Generic section splitting, shared with resumes | `parsing/section_utils.py` |
| JD section segmenter | `parsing/jd_sections.py` |
| Deterministic extractor | `parsing/heuristic_jd_extractor.py` |
| LLM extractor (dormant until a key is set) | `parsing/llm_jd_extractor.py` |
| Selection + guaranteed fallback | `parsing/jd_extractor_selector.py` |
| Placeholder title/company replaced by parsed values; empty JD now `422`; `GET /jd/{id}`, `GET /jd/list` | `api/v1/jd_routes.py` |
| Scorer matches `normalized_mandatory`, reads `min_experience_years` | `alignment/scorer.py` |

**Before → after on the same posting:**

| Field | Phase 2 | Phase 3 |
|---|---|---|
| `company` | `""` | `Acme Technologies` |
| `preferred` | `["nice to have"]` (the cue phrase) | `["Kubernetes", "Terraform", "Kafka"]` |
| `mandatory` | 8 skills, mixing must-haves with nice-to-haves | 5 genuine must-haves |
| `"Backend"` from the job title | counted as a required skill | never read from the title |
| `responsibilities` | the whole JD as one blob | 2 real bullets |
| `location` / `work_mode` / `employment_type` | absent | `Bengaluru, India` / `hybrid` / `Full-Time` |
| `seniority` / experience | `"Senior (5+ years)"` string | `seniority: senior`, `min_experience_years: 5` |
| stored JD title | `"Target Role"` for every row | parsed role |

Two latent bugs were found and fixed along the way:
- Section aliases were not normalised the way header lines were, so `What we're looking for`
  and the resume's `extra-curricular` could never match.
- The resume writes "backends" (plural) while the JD writes "backend", producing a phantom
  missing skill. Plural aliases are now explicit (a blanket trailing `s` would have made
  "reacts" match React).

Test suite: **90 passed** (was 62).

### Phase 4 — alignment & ATS scoring redesign ✅
Scoring now uses the data Phases 2–3 extract — see [backend/docs/scoring-engine.md](backend/docs/scoring-engine.md).

| Component | File |
|---|---|
| Weighted skill matching, partial credit, P1/P2/P3 gaps | `alignment/skill_matcher.py` |
| Responsibility overlap, project relevance, seniority | `alignment/components.py` |
| Deterministic 5-component ATS score | `ats/ats_engine.py` |
| ATS entry point + optional LLM feedback | `ats/ats_scorer.py` |
| Optional LLM layer (responsibility + prose only) | `alignment/llm_enhancer.py` |
| Component combination with renormalisation | `alignment/scorer.py` |
| Full breakdown persisted for later features | `alignment/persistence.py` |
| Skill categories for partial credit | `parsing/skill_vocabulary.py` |

**What changed:**

| | Before | After |
|---|---|---|
| `ats_score` | literally `min(100, alignment + 3)` | 5 real components per `docs/ats-scoring-engine.md` |
| `ATSScorerService` | existed, called from nowhere | wired, deterministic, LLM optional |
| Alignment components | skills .70, experience .30 | skills .40, responsibilities .20, projects .20, seniority .20 |
| Missing input | scored as zero | component dropped, weights renormalise |
| Skill weighting | all equal | title/frequency weighted |
| `preferred_skills` | parsed, unused | bonus that adds but never subtracts |
| Docker vs Kubernetes | scored zero | 0.4 partial credit, reported as `partial_skills` |
| Gaps | flat lowercase list | display names, ranked P1/P2/P3 |
| `responsibilities`, `projects[].tech_stack` | parsed, unused | scored components |

**Discrimination** — same resume, two postings:

```
                        relevant backend role    principal SRE role
alignment_score                        72.31                 10.97
skill_match                            90.77                 10.00
responsibility_match                  100.00                 15.87
seniority_match                        63.33                 19.00
```

The LLM layer can only set `responsibility_match` and rewrite prose; it can never move
`skill_match`, `project_match`, `seniority_match`, or any ATS number, so the headline figures
stay reproducible whether or not a key is configured.

Test suite: **126 passed** (was 90).

### Phase 5 — persistence & read-back ✅
See [backend/docs/persistence-and-readback.md](backend/docs/persistence-and-readback.md).

| Component | File |
|---|---|
| Alignment history queries, `latest_only`, pagination | `repositories/alignment_repo.py` |
| Content-hash lookup for idempotent upload | `repositories/resume_repo.py` |
| `AlignmentSummarySchema` / `AlignmentDetailSchema`; `alignment_id` on generate | `schemas/analytics.py` |
| `GET /alignment/list`, `GET /alignment/{id}` | `api/v1/alignment_routes.py` |
| Dedupe on upload + `duplicate_of_existing` flag; pagination | `api/v1/resume_routes.py` |
| Stale-payload tolerance (`entries()`) | `schemas/structured.py` |

- **Dedupe** keys on the SHA-256 of the file bytes. Re-uploading returns the existing record with
  no second file and no re-parse. `uploads/` had 14 PDFs for 2 distinct resumes; existing files
  were left in place by decision.
- **History** is appended on every generate, so score movement over time is recoverable.
  `latest_only=true` collapses to the newest run per pair via Postgres `DISTINCT ON`.
- **List returns scores only**; the full breakdown comes from the detail endpoint.
- `alignment_id` is now returned by `/alignment/generate`, as `api-design.md` always specified.

**A real bug surfaced here.** Dedupe returned a resume row stored before Phase 2, whose
`structured_data` kept `experience` as a list of strings. The Phase 4 scorer expects objects and
crashed with `AttributeError: 'str' object has no attribute 'get'`. `schema_version` existed for
exactly this but nothing checked it on read. Fixed on both levels: the scorer now re-parses any
payload that is not the current schema, and readers go through `entries()`, which skips
non-mapping list items. Regression tests added.

Test suite: **141 passed** (was 126).

### Phase 6 — resume optimizer (Step 4) ✅
See [backend/docs/optimization-engine.md](backend/docs/optimization-engine.md).

| Component | File |
|---|---|
| Anti-fabrication guardrail | `optimization/fact_guard.py` |
| Evidenced-skill promotion | `optimization/skill_promoter.py` |
| JD-relevance reordering | `optimization/reorderer.py` |
| Per-bullet advice | `optimization/bullet_advisor.py` |
| LLM rewriting behind the guard | `optimization/llm_bullet_rewriter.py` |
| Orchestration, change log, before/after | `optimization/engine.py` |
| Shared layout + text/.docx/PDF writers | `documents/layout.py`, `documents/writers.py` |
| Version history + downloads | `repositories/version_repo.py`, `api/v1/resume_routes.py` |
| Extra version columns | migration `b7d2f1a4c803` (applied) |

`POST /resume/optimize` was a `501`; it now returns a stored version with both download formats.
Added `GET /resume/{id}/versions` and `GET /resume/versions/{id}/download?format=docx|pdf`.

**Nothing is invented, and that is enforced mechanically:** skills are promoted only when already
evidenced in the resume, and every LLM rewrite is diffed against its original and discarded if it
introduces a figure, technology, or name that was not there. Verified against the live model —
it blocked rewrites adding "microservices" and "backend".

Measured on a weak resume: `ATS 52.0 → 85.0`, `Alignment 37.5 → 75.0`. On an already-strong
resume the delta is `0.0`, which is correct: with skill match, responsibility match, and keyword
coverage already at 100, the only remaining gaps are project relevance and years of experience,
neither closable honestly.

**Two prerequisites had to be fixed first.** `google-generativeai` was pinned at `0.4.1`, which
predates Gemini 1.5 GA and cannot route current models (now `0.8.6`). And `GeminiProvider` mapped
every non-`user` role to `"model"`, so the system prompts written in Phases 2–4 were replayed as
model turns — the model saw its own instructions as something it had already said. Both fixed and
live-verified. Note that `gemini-2.0-flash` has **zero** free-tier quota
(`limit: 0`) and `gemini-1.5-flash` is retired; the default is now `gemini-2.5-flash`.

Test suite: **179 passed** (was 141).

### Still outstanding (later phases)
- Step 5 (Analytics) is still not wired; `/dashboard/summary` and `/learning/roadmap` still
  return hardcoded values — **Phase 7**.
- The frontend still never displays the extracted data, the score breakdown, or the optimizer
  output — **Phase 8**.
- JD URL fetching is not implemented; the UI's URL field is unused — deferred.
- Embeddings/`pgvector` remain unused; `cultural_fit_score` is still unpopulated.
- No delete endpoints; ownership is still the demo user, so lists are not per-user scoped.
- `google-generativeai` is the deprecated SDK line; migrating to `google-genai` is a future task.

---

## 12. Verified evidence (as found during analysis)

| Claim | How it was verified |
|---|---|
| No PDF/DOCX libraries | `pip list` in `.venv` — no pdf/docx packages; absent from `requirements.txt` |
| Placeholder text is stored | Code trace of `_looks_like_binary()` → `_decode_text()` → `parse()` |
| Real PDFs are being uploaded | `backend/uploads/` contains 8 PDFs (3 distinct, ~72KB each) |
| No API keys configured | `.env`: `OPENAI_API_KEY` is the 8-char placeholder `sk-...`; Groq/Gemini empty |
| Alignment endpoint 422s | FastAPI scalar params bind to query; frontend posts a JSON body |
| Tests fail | `pytest tests -q` → **2 failed, 1 passed** |
| PostgreSQL reachable | `pg_isready -h localhost -p 5432` → accepting connections |
| LLM never used in parsing | No `AIFactory` import in either parser module |
