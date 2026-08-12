# ATS Scoring Engine

> **Status: implemented.**
> Built as [backend/docs/scoring-engine.md](../backend/docs/scoring-engine.md).
>
> All five components and their documented weights are as specified. Deviation: the engine is
> **deterministic** rather than LLM-based, so scores are reproducible and cost nothing. Structural
> safety is read from the extraction record, which catches an image-only PDF that no parser can
> read.


## Overview
The ATS (Applicant Tracking System) Scoring Engine evaluates a resume based on the technical "readability" and "parseability" by typical HR software.

## Scoring Categories

### 1. Keyword Density (40%)
- **Logic**: Counts frequency and placement of keywords identified in the JD.
- **Ideal Range**: 2-5% density per keyword.

### 2. Formatting & Structure (20%)
- **Detection**: Checks for complex layouts, multiple columns, images, or non-standard fonts that break basic parsers.
- **Score**: Binary flag for "ATS-Safe" structure.

### 3. Metrics Detection (20%)
- **Logic**: NLP-based detection of quantifiable achievements (e.g., "$5M revenue", "30% efficiency gain").
- **Weighted Value**: Resumes with higher "metric-to-bullet" ratios score better.

### 4. Section Completeness (10%)
- **Checklist**: Summary, Experience, Skills, Education, Contact.
- **Missing sections reduce the score.**

### 5. Bullet Clarity (10%)
- **Score**: Evaluates length, action verb usage, and cognitive complexity of bullet points.

## Weighted Scoring Formula
```python
ats_score = sum([
    keyword_score * 0.40,
    format_score * 0.20,
    metrics_score * 0.20,
    section_score * 0.10,
    clarity_score * 0.10
])
```

## Data Output Example
```json
{
  "total_ats_score": 88,
  "breakdown": {
    "keyword_density": 95,
    "structural_safety": 100,
    "impact_metrics": 70,
    "section_health": 100,
    "bullet_clarity": 85
  },
  "critical_warnings": [
    "Increase number of quantifiable metrics in Experience section.",
    "Consider adding 'PostgreSQL' keyword mentioned 4 times in JD."
  ]
}
```

## Future Extensibility
- Simulation against specific ATS platforms (Workday, Taleo).
- Real-time heatmaps for keyword density.
