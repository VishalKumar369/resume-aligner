# Analysis persistence

## Persistence model
The analysis feature stores three main types of data:
- Resume records with raw text and structured JSON
- Job description records with raw text and structured JSON
- Alignment score records with score values and analysis details

## Why this matters
Persisting the parsed information makes the project reusable for:
- future optimization prompts
- analytics dashboards
- skill-gap recommendations
- learning roadmaps
