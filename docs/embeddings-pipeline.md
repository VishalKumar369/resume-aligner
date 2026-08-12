# Embeddings Pipeline

> **Status: not implemented.**
>
> Nothing in this document was built. No embeddings are generated, `pgvector` is not used, and no
> table has a vector column. `app/services/resume/embedding.py` is not called by anything.
>
> Semantic matching is instead approximated deterministically — a canonical skill vocabulary with
> aliases, plus content-word overlap for responsibilities. See
> [backend/docs/scoring-engine.md](../backend/docs/scoring-engine.md). This document remains as the
> design for a future semantic upgrade.


## Overview
The Embeddings Pipeline converts unstructured text from resumes and job descriptions into high-dimensional vectors for semantic comparison using `text-embedding-3-large`.

## Pipeline Logic
```text
[Input Text] --> [Text Chunker] --> [OpenAI Embeddings API] --> [Normalizer] --> [pgvector Store]
```

### 1. Vector Generation
- **Model**: OpenAI `text-embedding-3-large`.
- **Dimensions**: 3072.
- **Preprocessing**: Removal of PII (optional), white-space normalization, and truncation to 8192 tokens.

### 2. Similarity Scoring
We use **Cosine Similarity** to calculate the distance between a Resume vector ($A$) and a JD vector ($B$).

$$ \text{Similarity}(A, B) = \frac{A \cdot B}{\|A\| \|B\|} $$

### 3. pgvector Integration
We use `pgvector` for efficient vector operations within PostgreSQL.

**Schema Design:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE resumes ADD COLUMN embedding vector(3072);
ALTER TABLE job_descriptions ADD COLUMN embedding vector(3072);

-- Creating HNSW index for fast discovery
CREATE INDEX ON resumes USING hnsw (embedding vector_cosine_ops);
```

### 4. Semantic Search Query
To find resumes similar to a specific JD embedding:
```sql
SELECT id, 1 - (embedding <=> :jd_embedding) AS similarity
FROM resumes
ORDER BY similarity DESC
LIMIT 10;
```

## Ranking Logic
The semantic score is combined with metadata flags (e.g., "years of experience") to create a final rank. Pure semantic similarity is the baseline, while rule-based filters act as multipliers.
