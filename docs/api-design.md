# API Design

## Overview
The API is built using FastAPI following RESTful principles. All endpoints return JSON and use JWT for authentication.

---

### POST `/resume/upload`
Uploads a resume file and triggers the parsing/embedding pipeline.

**Request:** `Multipart/Form-Data`
```json
{
  "file": "binary_data.pdf",
  "label": "Main Tech Resume"
}
```

**Response:** `202 Accepted`
```json
{
  "task_id": "8c3b4-...",
  "status": "processing",
  "message": "Resume upload successful. Extraction in progress."
}
```

---

### POST `/jd/upload`
Uploads a job description text or URL.

**Request:** `application/json`
```json
{
  "raw_text": "Looking for a Senior Python Developer with 5 years exp...",
  "url": "https://company.com/careers/123",
  "company_name": "Tech Corp"
}
```

**Response:** `200 OK`
```json
{
  "jd_id": "jd_776",
  "structured_summary": {
    "title": "Senior Python Developer",
    "required_skills": ["Python", "FastAPI", "SQL"]
  }
}
```

---

### POST `/alignment/generate`
Generates an alignment score between a resume and a specific JD.

**Request:** `application/json`
```json
{
  "resume_id": "res_123",
  "jd_id": "jd_456"
}
```

**Response:** `200 OK`
```json
{
  "overall_score": 85.5,
  "factors": {
    "skill_match": 90,
    "seniority_match": 70,
    "culture_fit_index": 82
  },
  "alignment_id": "align_99"
}
```

---

### POST `/resume/optimize`
Triggers the optimization engine to create a tailored resume version.

**Request:** `application/json`
```json
{
  "resume_id": "res_123",
  "jd_id": "jd_456",
  "focus_area": "Machine Learning"
}
```

**Response:** `200 OK`
```json
{
  "version_id": "v_1.1",
  "download_url": "https://s3.amazonaws.com/...",
  "changes_made": [
    "Rewrote Python exp to emphasize FastAPI",
    "Injected 'Distributed Systems' keyword"
  ]
}
```

---

### GET `/dashboard/summary`
Retrieves aggregated career readiness and recent activity.

**Response:** `200 OK`
```json
{
  "career_readiness_score": 78,
  "top_missing_skills": ["Kubernetes", "Redis"],
  "recent_alignments": [
    { "company": "Google", "score": 92 },
    { "company": "Stripe", "score": 65 }
  ],
  "interview_probability": "High"
}
```

---

### GET `/learning/roadmap`
Fetches the personalized learning path based on JD gaps.

**Response:** `200 OK`
```json
{
  "roadmap": [
    {
      "skill": "Docker",
      "priority": "High",
      "resources": ["udemy.com/docker", "docs.docker.com"],
      "eta": "2 weeks"
    }
  ]
}
```
