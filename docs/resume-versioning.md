# Resume Versioning

## Overview
Every time a resume is optimized or tailored for a specific JD, a new version is created. This allows users to track their progress and manage multiple submissions.

## Versioning Strategy
- **Base Resume**: The original master document uploaded by the user.
- **Tailored Variants**: Branches of the master resume optimized for specific companies or roles.

## File Storage
- **Protocol**: S3-compatible (AWS S3, MinIO, or Cloudflare R2).
- **Structure**: `s3://bucket-name/users/{user_id}/resumes/{resume_id}/versions/{version_id}.pdf`

## Database Indexing
The `resume_versions` table tracks:
- `s3_path`
- `target_jd_id`
- `diff_summary`: A summary of changes from the base version.
- `ats_score`: The score specific to this variant.

## User Flow
1. User clicks "Optimize for Google".
2. Engine creates a new PDF.
3. S3 URL is generated and stored.
4. User can download current version or "Roll back" to a previous variant.

## Change Tracking
The system stores a JSON diff between versions to highlight exactly what was changed for the user.
