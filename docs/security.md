# Security

## Overview
Security is a top priority, focusing on data privacy, secure LLM interactions, and PII protection.

## Core Security Pillars

### 1. Authentication & Authorization
- **JWT**: Stateless authentication using JSON Web Tokens.
- **RBAC**: Role-Based Access Control (Admin vs. User).
- **CORS**: Restricted cross-origin resource sharing to trusted domains.

### 2. File Upload Validation
- **Scan**: Uploaded resumes are scanned for malicious macros/payloads.
- **Limits**: Max file size: 5MB. Allowed formats: `.pdf`, `.docx`, `.txt`.

### 3. PII Protection
- **Strategy**: Before sending resume text to LLM providers, sensitive fields (Phone, Address, Specific IDs) are optionally masked or anonymized.
- **Encryption**: Data at rest (RDS) and in transit (TLS 1.3).

### 4. LLM Prompt Sanitization
- **Injecion Prevention**: User inputs (JD/Resume) are sanitized to prevent prompt injection attacks that might try to leak system prompts or change scoring logic.

### 5. API Rate Limiting
- **Redis-backed**: Global and per-user rate limits to prevent brute force and API abuse (especially for expensive LLM endpoints).

## Data Encryption
- **RDS**: AES-256 encryption at rest.
- **S3**: Server-side encryption (SSE-S3).

## Compliance
- **GDPR Ready**: Data deletion endpoints (Right to be Forgotten) implemented.
- **Audit Logs**: Tracking all document access and scoring events.
