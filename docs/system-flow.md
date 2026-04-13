# System Flow

## End-to-End Workflow Diagram
```text
USER                  FRONTEND              BACKEND              ENGINES              DB/STORAGE
  |                      |                     |                    |                     |
  |-- Upload Resume ---->|                     |                    |                     |
  |-- Upload JD -------->|--- POST /upload --->|                    |                     |
  |                      |                     |--[ Queue Task ]--->|                     |
  |                      |                     |                    |-- Parse Resume ---->|
  |                      |                     |                    |-- Parse JD -------->|
  |                      |                     |<--[ Task Ready ]---|                     |
  |                      |<--- Notify Done ----|                    |                     |
  |                      |                     |                    |                     |
  |-- Click Align ------>|--- POST /align ---->|                    |                     |
  |                      |                     |--[ Generation ]--->|-- Embedding Gen --->|
  |                      |                     |                    |-- Similarity Scorp->|
  |                      |                     |                    |-- Skill Gap Detect->|
  |                      |                     |<--[ Results ]------|                     |
  |                      |<--- Display Dash ---|                     |                     |
  |                      |                     |                    |                     |
  |-- Optimize --------->|--- POST /optimize ->|                    |                     |
  |                      |                     |--[ LLM Chain ]---->|-- Rewrite Bullets ->|
  |                      |                     |                    |-- Store Version --->|
  |                      |<--[ New Resume ]----|                    |                     |
  |                      |                     |                    |                     |
```

## Detailed Flow Steps

### 1. Ingestion & Extraction
- **Resume Parser**: PDF is converted to markdown or raw text. An LLM (GPT-4o) extracts entities: `skills`, `experience`, `projects`, `education`.
- **JD Parser**: Extracts `required_skills`, `nice_to_have`, `responsibilities`, `company_culture`.

### 2. Embedding & Alignment
- Extracted entities are converted into embeddings using `text-embedding-3-large`.
- **Cosine Similarity**: Performed using `pgvector` to find the distance between Resume vectors and JD vectors.
- **Weighted Alignment**: Scores are calculated based on skill overlap, seniority match, and project relevance.

### 3. Optimization
- The current resume and the target JD are sent to the **Optimization Engine**.
- AI rewrites bullet points to mirror JD language while maintaining truthfulness.
- Keywords are strategically injected into the "Skills" and "Summary" sections.

### 4. Analytics & Dashboard
- Calculations for `Career Readiness`, `Interview Probability`, and `Market Alignment` are performed.
- Results are aggregated into a `dashboard_snapshot` for high-speed retrieval.

### 5. Storage & Versioning
- Every optimized resume is saved as a new version in S3.
- Metadata (scores, changes made) is saved in the `resume_versions` table.
