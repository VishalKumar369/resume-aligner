# Job Description (JD) Parser

## Overview
The JD Parser extracts critical requirements and company culture insights from job postings.

## Core Responsibilities
- **Entity Extraction**: Identify required tech stack, years of experience, and degrees.
- **Priority Detection**: Distinguish between "Required" and "Nice to have" skills.
- **Culture Mapping**: Detect keywords related to company values (e.g., "fast-paced", "collaborative").

## Data Schema (Output)
```json
{
  "role": "Backend Engineer",
  "company": "Amazon",
  "requirements": {
    "mandatory": ["AWS", "Java", "SQL"],
    "preferred": ["Rust", "Kubernetes"]
  },
  "experience_level": "Senior (5+ years)",
  "location": "Remote / Seattle",
  "salary_range": "...",
  "key_responsibilities": ["Scale cloud infra", "Mentor juniors"]
}
```

## Pipeline Logic
- **Input Types**: Raw text, HTML (from scraper), or Markdown.
- **Extraction Logic**: Uses a specific system prompt optimized for high-density information extraction from job boards.
- **Market Demographics**: Enriches the data with market benchmarks for specific titles.

## Future Extensibility
- Direct API integration with Lever, Greenhouse, and Workday.
- Automated salary benchmark comparison.
