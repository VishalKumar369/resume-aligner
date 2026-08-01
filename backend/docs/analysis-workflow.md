# Analysis workflow

## Overview
The analysis flow starts with a resume upload and a job description upload. The backend parses both into structured JSON, stores the results, and uses them to compute alignment scores.

## Pipeline
1. Upload resume
2. Extract raw text from the uploaded file
3. Parse structured resume data
4. Upload JD and parse structured requirements
5. Compute alignment and save the result

## Data contracts
### Resume structured data
- personal_info
- skills
- experience
- education
- projects
- certifications

### JD structured data
- role
- company
- experience_level
- requirements
- responsibilities
- keywords

## Future reuse
The persisted structured data will feed optimization, dashboard analytics, skill-gap analysis, and learning recommendations.
