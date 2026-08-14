# Dashboard Analytics

> **Status: implemented, with one deliberate omission.**
> Built as [backend/docs/analytics-and-learning.md](../backend/docs/analytics-and-learning.md).
>
> **Interview probability is not a logistic regression model.** No hiring-outcome data exists
> here, so rather than dress a guess up as a prediction the endpoint returns a transparent band
> that ships its own formula and a caveat stating it is a heuristic. Career readiness and the
> skill heatmap are as specified; there is no industry benchmark dataset for the resume strength
> index.


## Overview
Aggregates all engine outputs into high-level metrics for the user to track career progression.

## Key Metrics

### 1. Career Readiness Score
A holistic index (0-100) representing how "ready" a user is for their target roles across all saved JDs.
- **Formula**: Average(Alignment Scores) Weighted by JD Priority.

### 2. Resume Strength Index
Evaluates the candidate's primary resume against industry benchmarks for their specific title.

### 3. Skill Heatmap
A visual representation of the candidate's skills vs. market demand and target JD requirements.

### 4. Interview Probability Estimation
Uses a logistic regression model (or LLM estimation) trained on historical hiring data to predict the likelihood of getting an interview based on the alignment score.

## Data Schema (Snapshot)
```json
{
  "readiness_trend": [70, 72, 75, 82],
  "probability_index": 0.65,
  "top_companies_match": [
    { "name": "Google", "score": 88 },
    { "name": "Meta", "score": 82 }
  ]
}
```

## UI Elements
- **Ready-Meter**: Circular gauge showing readiness.
- **Gap Chart**: Horizontal bars showing missing skills vs. time to acquire.
