# Company Intelligence Engine

## Overview
This engine provides insights into specific company hiring patterns, cultures, and technical preferences.

## Data Sources
- **Public Filings/Postings**: Extraction of recurring tech stack requirements.
- **Glassdoor/Indeed APIs**: Sentiment analysis on culture and interview processes.
- **Tech Blogs**: Tracking recent shifts in engineering focus (e.g., moving from Monolith to Microservices).

## Analysis Types
1. **Culture Fit Score**: Measures how well the candidate's professional style (extracted from resume) matches the company's stated values.
2. **Tech Preference Mapping**: Maps if a company prefers specific tools (e.g., AWS vs GCP).
3. **Interview Insights**: Aggregates common interview questions for specific roles at that company.

## API Usage
`GET /company/{id}/insights`

## Metadata Example
```json
{
  "company": "Stripe",
  "culture_tags": ["High bar", "Writing culture", "Developer focused"],
  "primary_stack": ["Ruby on Rails", "Go", "AWS"],
  "hiring_status": "Aggressive",
  "prep_tips": "Focus on system design and clean API documentation."
}
```
