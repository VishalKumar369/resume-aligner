# Analysis feature implementation guide

## Scope implemented
The first backend analysis workflow is now wired so the app can:
- accept a resume upload and parse it into structured JSON
- accept a job description and parse it into structured JSON
- compute alignment and ATS-like scores from those structures
- persist the parsed data and alignment results for future features

## Backend files
- [backend/app/api/v1/resume_routes.py](backend/app/api/v1/resume_routes.py)
- [backend/app/api/v1/jd_routes.py](backend/app/api/v1/jd_routes.py)
- [backend/app/api/v1/alignment_routes.py](backend/app/api/v1/alignment_routes.py)
- [backend/app/services/parsing/resume_parser.py](backend/app/services/parsing/resume_parser.py)
- [backend/app/services/parsing/jd_parser.py](backend/app/services/parsing/jd_parser.py)
- [backend/app/services/alignment/scorer.py](backend/app/services/alignment/scorer.py)
- [backend/app/services/alignment/persistence.py](backend/app/services/alignment/persistence.py)
- [backend/docs/analysis-workflow.md](backend/docs/analysis-workflow.md)
- [backend/docs/analysis-persistence.md](backend/docs/analysis-persistence.md)

## Data flow
1. Resume upload stores the file, raw text, and structured resume JSON.
2. JD upload stores the raw JD text and structured JSON.
3. Alignment generation loads the persisted resume/JD records and computes a score payload.
4. The result is persisted in the alignment table for future dashboard and optimization features.

## Notes for future work
- Add real PDF/DOCX parsing with libraries such as pypdf or python-docx.
- Replace the heuristic parser with an LLM-backed extraction step when API keys are available.
- Connect the frontend upload page to the new backend APIs.
