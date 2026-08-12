# Getting started

Running the project locally. Verified on Linux with Python 3.10 and Node 18+.

## Prerequisites

- **Python 3.10+**
- **Node 18+**
- **PostgreSQL 14+**, running and reachable

No Docker or Kubernetes configuration exists yet — see
[deployment-architecture.md](deployment-architecture.md).

## 1. Database

```bash
createdb resume_jd_aligner          # or via your preferred client
pg_isready -h localhost -p 5432     # should report "accepting connections"
```

`pgvector` is **not** required — no vector columns exist.

## 2. Backend

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

cp backend/.env.example backend/.env
# set SQLALCHEMY_DATABASE_URI and SECRET_KEY

cd backend && ../.venv/bin/python -m alembic upgrade head
../.venv/bin/python -m uvicorn app.main:app --port 8000 --reload
```

API at `http://localhost:8000`, interactive docs at `/docs`.

### Environment

The values that matter for a first run:

| Variable | Purpose |
|---|---|
| `SQLALCHEMY_DATABASE_URI` | `postgresql+asyncpg://user:pass@localhost:5432/resume_jd_aligner` |
| `SECRET_KEY` | Signs JWTs. Change it from the example |
| `UPLOAD_DIR` | Where uploads and generated documents are written |

Everything else has a working default.

### AI provider (optional)

The application runs fully without an API key — extraction, scoring, and analytics are all
deterministic. A key only adds **bullet rewriting** in the optimizer.

```bash
AI_PROVIDER="gemini"
GEMINI_API_KEY="..."       # free key: aistudio.google.com/apikey
GEMINI_MODEL="gemini-2.5-flash"
```

Two things worth knowing before enabling it:

- Free tiers are metered **per day** (Gemini reported a limit of 20/day for a free project), so
  only bullet rewriting is switched on by default. See
  [backend/docs/llm-budget.md](../backend/docs/llm-budget.md).
- `gemini-2.0-flash` has zero free-tier quota and `gemini-1.5-flash` is retired. Use
  `gemini-2.5-flash`.

## 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

App at `http://localhost:3000`. `frontend/.env.local` needs `NEXT_PUBLIC_API_URL` pointing at the
backend (`http://localhost:8000` by default).

## 4. First run

1. Open `http://localhost:3000` and **sign up** — every data endpoint requires a token, and each
   account sees only its own data.
2. Go to **Upload**, drop in a PDF or DOCX resume.
3. Check the extraction review panel. If the name, dates, or skills look wrong, replace the file
   before continuing — everything downstream builds on this.
4. Paste a job description, then walk through alignment, optimization, and analytics.

## Tests

```bash
cd backend && ../.venv/bin/python -m pytest tests -q     # 237 tests
cd frontend && npx tsc --noEmit                          # types
cd frontend && npm run build                             # full build
```

The backend suite needs no database and no API key — every LLM path is tested against a fake
provider.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `401` on every request | Not signed in, or the token expired. The frontend clears it and redirects to login |
| `422` on resume upload | The PDF has no text layer (a scan). OCR is not implemented — use a text-based PDF or DOCX |
| `415` on upload | Not a PDF, DOCX, or text file. Type is detected from magic bytes, not the extension |
| Upload returns an existing record | Working as intended — identical bytes are deduped |
| Optimizer says "daily quota" | The provider's daily limit is spent; rewriting falls back to suggestions |
| Dashboard is empty | No alignment runs yet. `has_data: false` drives the empty state |
| `alembic` errors on start | Migrations not applied — run `alembic upgrade head` |
