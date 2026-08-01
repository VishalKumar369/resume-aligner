# Frontend and backend integration plan

## Backend status
The backend now has the first analysis workflow implemented.

## Frontend next steps
1. Connect the upload page to the resume upload endpoint.
2. Connect the JD input step to the JD upload endpoint.
3. Call the alignment generation endpoint after both objects exist.
4. Replace the mock progress and metric values with API results.

## Recommended API payloads
### Resume upload
- file: binary file
- label: optional string

### JD upload
- title: string
- company_name: optional string
- raw_text: string
- url: optional string

### Alignment generation
- resume_id: UUID
- jd_id: UUID
