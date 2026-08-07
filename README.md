# Resume-JD-Aligner

Production-grade AI platform for ATS-optimized resume generation, hiring readiness analytics, and career roadmap planning.

## Overview
`resume-jd-aligner` is a sophisticated AI-driven platform that bridges the gap between candidates and job descriptions. It leverages Large Language Models (LLMs) and Vector Databases to provide deep semantic analysis of resumes against specific job requirements.

### Problem Statement
Most ATS (Applicant Tracking Systems) use keyword matching, causing many qualified candidates to be filtered out due to formatting or specific terminology. Furthermore, candidates often lack clear visibility into why they are not a match for a role or how to bridge their skill gaps.

### Solution Vision
A comprehensive suite that not only "hacks" the ATS score but truly aligns a candidate's profile with the JD, providing actionable learning paths and company-specific resume variants.

---

## Core Features
- 🚀 **ATS Scoring & Optimization**: Detailed analysis of keyword density, formatting, and section completeness.
- 🎯 **Semantic Alignment Engine**: Vector-based matching for skill, project, and responsibility overlap.
- 📝 **Company-Specific Resume Generation**: AI-driven variant generation tailored to specific company cultures.
- 🗺️ **Learning Roadmap**: Automated detection of skill gaps with prioritized learning resources.
- 📊 **Hiring Readiness Analytics**: Interview probability scores and dashboard-level career tracking.

---

## Architecture Summary
The system follows a modern microservice-ready modular monolith architecture.

- **Frontend**: Next.js (App Router), Tailwind CSS, Framer Motion.
- **Backend**: FastAPI (Python 3.11+), Celery (Background Tasks).
- **Database**: PostgreSQL with `pgvector` for semantic search.
- **Cache/Queue**: Redis.
- **AI/ML**: OpenAI GPT-4o, `text-embedding-3-large`.
- **Storage**: AWS S3 or MinIO for document versioning.

---

## System Workflow Diagram
```text
[Candidate] --> (Resume Upload) --+
                                  |
[Job Link]  --> (JD Scraper)    --+--> [Parsing Layer]
                                           |
                                     (JSON Extraction)
                                           |
                                    [Embedding Layer]
                                           |
                                 (pgvector / PostgreSQL)
                                           |
    +--------------------------------------+--------------------------------------+
    |                                      |                                      |
[Alignment Engine]                 [ATS Scoring Engine]                 [Skill Gap Engine]
    |                                      |                                      |
[Resume Optimizer]              [Dashboard Aggregator]               [Learning Roadmap]
    |                                      |                                      |
[Tailored Resume] <--------------- [Interactive UI] <-------------- [Career Analytics]
```

---

## Folder Structure
```text
resume-jd-aligner/
├── backend/            # FastAPI Project
│   ├── app/            # Main logic
│   ├── db/             # pgvector schemas
│   └── engines/        # Scoring & Ranking logic
├── frontend/           # Next.js Application
├── docs/               # Technical Documentation
├── infra/              # Docker & Kubernetes configs
└── scripts/            # Data migration & utility tools
```

---

## Setup & Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (with pgvector extension)
- Redis

### Environment Variables
Create a `.env` file in the root:
```env
# API Keys
OPENAI_API_KEY=sk-...
S3_BUCKET_NAME=resume-versions

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/resume_db

# Redis
REDIS_URL=redis://localhost:6379/0
```

### Installation
1. **Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   python main.py
   ```
2. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## Roadmap Phases
- **Phase 1**: Core Parser & Alignment Engine.
- **Phase 2**: ATS Optimization & Skill Gap Detection.
- **Phase 3**: Company-specific Generation & Learning Roadmap.
- **Phase 4**: Advanced Analytics & Predictive Interview Readiness.

---

## Contribution Guidelines
1. Fork the repository .
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes.
4. Push to the branch.
5. Open a Pull Request.

## Future Scope
- Integration with LinkedIn/Indeed APIs.
- Real-time market demand trend analysis.
- Multi-language resume support.
- AI-driven cover letter generator.
