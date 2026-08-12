# System Architecture

> **Status: partly implemented.**
> Next.js frontend, FastAPI backend, and PostgreSQL are as described.
>
> Not built: **Redis, Celery workers, and the async engine cluster.** Everything runs
> synchronously in the API process. `REDIS_URL` and `USE_REDIS` exist in config but no Redis
> client is instantiated, and `app/utils/cache.py` is unused dead code. The only caching in use is
> the database-backed LLM result cache, see
> [backend/docs/llm-budget.md](../backend/docs/llm-budget.md).


## Overview
Resume-JD-Aligner is designed as a modular platform to handle complex AI workflows, high-throughput parsing, and real-time analytics.

## Component Diagram
```text
+---------------------+       +-------------------------+       +----------------------+
|    Next.js Web      | <---> |    FastAPI Gateway      | <---> |   Redis (Cache/Bus)  |
|    (Frontend)       |       |       (Backend)         |       |                      |
+---------------------+       +-------------------------+       +----------------------+
                                          |                             |
                                          v                             v
                              +-------------------------+       +----------------------+
                              |    Engine Cluster       | <---> |   Celery Workers     |
                              | (Parser, Opt, Analytics)|       | (Async Heavy Tasks)  |
                              +-------------------------+       +----------------------+
                                          |
                   +----------------------+----------------------+
                   |                      |                      |
        +----------------------+ +----------------------+ +----------------------+
        |   PostgreSQL +       | |    OpenAI API        | |    S3 compatible     |
        |   pgvector (Data)    | | (Intelligence Layer) | |   (Version Storage)  |
        +----------------------+ +----------------------+ +----------------------+
```

## High-Level Data Flow
1. **Ingestion**: Resume (PDF/Docx) and JD (Text/URL) are uploaded via FastAPI.
2. **Parsing**: Background Celery workers parse files into structured JSON using LLM-assisted extractors.
3. **Embedding**: Extracted data is sent to the Embedding Pipeline to generate semantic vectors.
4. **Processing**: Specialized engines (Alignment, ATS, Skill Gap) process the vectors and JSON data.
5. **Storage**: Final versions and scores are stored in PostgreSQL and S3.
6. **Analytics**: Dashboard snapshots are generated for real-time frontend consumption.

## Service Responsibilities
- **Frontend**: State management, interactive resumes, data visualization.
- **Backend API**: Request orchestration, authentication, schema validation.
- **Parsing Service**: OCR/Text extraction and structured entity extraction.
- **Alignment Engine**: Vector similarity scoring and logic-based matching.
- **Optimization Engine**: Generative LLM logic for bullet point refinement.
- **Worker Node**: Handles long-running LLM calls and PDF generation.
