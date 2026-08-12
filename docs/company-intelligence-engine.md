# Company Intelligence Engine

> **Status: implemented differently, on purpose.**
> Built as [backend/docs/analytics-and-learning.md](../backend/docs/analytics-and-learning.md).
>
> The design called for Glassdoor/Indeed sentiment and tech-blog tracking. What was built reports
> **only what the user's own saved postings say** — roles, seniority, locations, demanded skills,
> and their alignment history. The previous placeholder returned an invented tech stack and
> interview tips for any company id, which is asserting facts about a real organisation from
> nothing. With no saved posting for a company the endpoint returns 404.
>
> Culture-fit scoring is not implemented; `alignment_scores.cultural_fit_score` stays null.


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
