# Resume-JD-Aligner

Analyses a resume against a job description, scores the match, and produces a tailored resume —
without inventing anything the resume does not support.

📚 **[Documentation index](docs/README.md)** · 🚀 **[Getting started](docs/getting-started.md)**

---

## What it does

Five steps, all working end to end:

1. **Upload a resume** — PDF or DOCX is parsed into structured JSON, and the app shows you exactly
   what it extracted so a bad parse is caught immediately.
2. **Add a job description** — requirements are separated from nice-to-haves, with seniority and
   experience read from the posting.
3. **Review alignment** — a weighted score with a per-component breakdown, matched, partially
   covered and missing skills, and gaps ranked by priority.
4. **Optimize** — evidenced skills promoted, content reordered by relevance, bullets rewritten,
   exported as `.docx` and PDF, stored as a version with before/after scores.
5. **View analytics** — career readiness, gaps common across your target roles, a learning roadmap,
   and per-company insights.

## Principles

These shaped most of the design decisions:

- **Nothing is invented.** Every rewritten bullet is diffed against its original and discarded if
  it adds a figure, technology, or name that was not there. Skills are only surfaced when already
  evidenced. Company insights report only what your own saved postings say.
- **A broken parse is never scored as a weak candidate.** Every alignment carries extraction
  health, so a 0% match is distinguishable from a file that could not be read.
- **Uncertainty is stated.** The interview signal ships its own formula and says plainly that it
  is a heuristic, not a model trained on hiring outcomes.
- **Deterministic by default.** Extraction and scoring use no AI and are fully reproducible. A
  model is optional and, by default, used only for rewriting prose.

## Stack

| Layer | What is actually used |
|---|---|
| Frontend | Next.js 14 (App Router), Tailwind, Framer Motion, Recharts, Zustand |
| Backend | FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2 |
| Database | PostgreSQL |
| Parsing | pdfplumber + pypdf, python-docx |
| Documents | python-docx, ReportLab |
| AI (optional) | Gemini / OpenAI / Groq — off by default except bullet rewriting |
| Storage | Local disk via a pluggable storage adapter |

**Not used**, despite appearing in the original design: `pgvector` and embeddings, Redis, Celery
workers, and S3. See [docs/README.md](docs/README.md) for what was built versus designed.

## Layout

```text
resume-jd-aligner/
├── backend/
│   ├── app/
│   │   ├── api/v1/          route handlers
│   │   ├── core/            config, security
│   │   ├── db/              session, declarative base
│   │   ├── models/          SQLAlchemy models
│   │   ├── repositories/    query layer
│   │   ├── schemas/         Pydantic contracts
│   │   └── services/        extraction, parsing, alignment, ats,
│   │                        optimization, documents, analytics, ai
│   ├── alembic/versions/    migrations
│   ├── tests/               237 tests, no DB or API key required
│   └── docs/                implementation documentation
├── frontend/
│   ├── app/                 pages (App Router)
│   ├── components/          UI and feature components
│   ├── hooks/ services/     data fetching and API client
│   └── docs/                frontend integration documentation
└── docs/                    index, references, design intent
```

## Quick start

```bash
# database
createdb resume_jd_aligner

# backend
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cp backend/.env.example backend/.env        # set SQLALCHEMY_DATABASE_URI and SECRET_KEY
cd backend && ../.venv/bin/python -m alembic upgrade head
../.venv/bin/python -m uvicorn app.main:app --port 8000 --reload

# frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open `http://localhost:3000` and **sign up** — every data endpoint is scoped to the signed-in
user. Full instructions and troubleshooting in [docs/getting-started.md](docs/getting-started.md).

Works with no AI key at all. Adding one enables bullet rewriting; see
[backend/docs/llm-budget.md](backend/docs/llm-budget.md) first, since free tiers are metered per
day.

## Tests

```bash
cd backend && ../.venv/bin/python -m pytest tests -q     # 237 tests
cd frontend && npm run build
```

## Status

The five-step flow is complete and documented. Known gaps are recorded honestly in
[docs/README.md](docs/README.md) and the phase log in
[docs/backend-analysis-and-redesign-plan.md](docs/backend-analysis-and-redesign-plan.md) — the
larger ones being OCR for scanned PDFs, JD fetching from a URL, semantic embeddings, and
deployment configuration.
