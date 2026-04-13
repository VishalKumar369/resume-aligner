# Database Schema

## Overview
The database uses PostgreSQL with the `pgvector` extension for semantic search capabilities.

## Entity Relationship Summary (ASCII)
```text
[Users] 1 --- N [Resumes]
[Resumes] 1 --- N [ResumeVersions]
[Resumes] 1 --- N [AlignmentScores]
[JobDescriptions] 1 --- N [AlignmentScores]
[ResumeVersions] 1 --- 1 [S3_Storage]
[Resumes] 1 --- N [SkillGaps]
[Resumes] 1 --- N [LearningPaths]
```

## Table Definitions

### `users`
| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Unique user identifier |
| `email` | VARCHAR(255) | User email (indexed) |
| `hashed_password` | TEXT | Securely hashed password |
| `created_at` | TIMESTAMP | Account creation time |

### `resumes`
| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Unique resume identifier |
| `user_id` | UUID (FK) | Reference to `users.id` |
| `raw_text` | TEXT | Full text extracted from PDF |
| `structured_data` | JSONB | Extracted entities (skills, exp, etc.) |
| `embedding` | VECTOR(3072) | text-embedding-3-large vector |
| `created_at` | TIMESTAMP | Upload time |

### `job_descriptions`
| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Unique JD identifier |
| `url` | TEXT | Source URL (optional) |
| `raw_text` | TEXT | Full JD text |
| `structured_data` | JSONB | Required skills, responsibilities |
| `embedding` | VECTOR(3072) | text-embedding-3-large vector |

### `resume_versions`
| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Version identifier |
| `resume_id` | UUID (FK) | Reference to `resumes.id` |
| `s3_path` | TEXT | Path to generated PDF/Docx |
| `variant_tag` | VARCHAR(50) | e.g., "Google-Optimized", "FinTech-Version" |
| `ats_score` | FLOAT | Score for this specific version |

### `skill_gaps`
| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Gap identifier |
| `resume_id` | UUID (FK) | Reference to `resumes.id` |
| `missing_skill` | VARCHAR(100) | Name of the skill |
| `priority` | INTEGER | 1 (High) - 5 (Low) |

### `dashboard_snapshots`
| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Snapshot identifier |
| `user_id` | UUID (FK) | Reference to `users.id` |
| `data` | JSONB | Aggregated scores and stats |
| `captured_at` | TIMESTAMP | Snapshot time |

## Indexes
- `idx_resumes_embedding`: HNSW index on `embedding` for fast similarity search.
- `idx_users_email`: B-tree index on email for login lookups.
- `idx_resumes_user`: B-tree index on `user_id`.
