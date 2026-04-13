# Resume Parser

## Overview
The Resume Parser is a dedicated service responsible for converting raw PDF/Docx files into a structured, machine-searchable JSON format.

## Parsing Strategy
1. **Extraction**: Uses `PyMuPDF` or `pdfminer.six` for raw text extraction.
2. **Structuring**: Utilizes a Few-Shot LLM Prompting strategy to map text to a predefined schema.

## Data Schema (Output)
```json
{
  "personal_info": { "name": "...", "contact": "..." },
  "summary": "...",
  "skills": {
    "hard_skills": ["Python", "Docker"],
    "soft_skills": ["Leadership", "Agile"]
  },
  "experience": [
    {
      "company": "Tech Inc",
      "role": "Senior Engineer",
      "duration": "2020 - 2023",
      "bullets": ["Managed team of 5", "Implemented CI/CD"]
    }
  ],
  "projects": [...],
  "education": [...]
}
```

## Parsing Pipeline
- **Step 1: Text Sanitization**: Remove encoding artifacts and excessive newlines.
- **Step 2: Section Identification**: Heuristic-based detection of headers (Experience, Skills, etc.).
- **Step 3: LLM Inference**: Pass sanitized text sections to GPT-4o with instructions to return JSON.
- **Step 4: Validation**: Schema validation using Pydantic models.

## Future Extensibility
- Support for images/charts using Vision-LLMs (GPT-4o Vision).
- Multi-language NER (Named Entity Recognition).
