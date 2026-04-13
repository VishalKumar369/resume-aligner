# Scaling Strategy

## Overview
To handle thousands of concurrent users and complex LLM pipelines, a multi-layered scaling strategy is implemented.

## Horizontal Scaling
- **API Nodes**: Scaled horizontally based on Request-Per-Second (RPS).
- **Worker Nodes**: Scaled based on the length of the Celery task queue (Seda - Staged Event-Driven Architecture).

## Implementation Details

### 1. Async Task Queues
- Long-running tasks (PDF Parsing, Embedding Generation, Optimization) are offloaded from the main API thread to **Redis + Celery**.
- This ensures the UI remains responsive while the heavy lifting happens in the background.

### 2. Batch Processing
- For high-volume users (e.g., recruiters), embedding generation is batched to reduce API round-trips to OpenAI.

### 3. Caching Strategy
- **Result Caching**: Results for identical Resume + JD pairs are cached in Redis for 24 hours.
- **Embedding Cache**: Computed embeddings for JDs are stored to avoid re-computation for multiple users.

### 4. Database Optimization
- **pgvector Indexing**: Using HNSW (Hierarchical Navigable Small World) for sub-linear search time as the database grows to millions of vectors.
- **Read Replicas**: Separate RDS read replicas for analytics-heavy dashboard queries.

### 5. Microservice Extraction
As the platform scales, the **Parser Engine** and **Analytics Engine** can be extracted into independent microservices with their own scaling policies.
