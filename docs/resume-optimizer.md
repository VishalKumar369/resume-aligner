# Resume Optimizer

> **Status: implemented.**
> Built as [backend/docs/optimization-engine.md](../backend/docs/optimization-engine.md).
>
> "DO NOT fabricate experience" is enforced **mechanically**, not by prompting: every rewrite is
> diffed against its original and discarded if it introduces a figure, technology, or name that
> was not there. Keyword injection is limited to skills already evidenced in the resume.
>
> Not built: company-specific startup/enterprise modes, and metric enhancement advises rather
> than inserting placeholder numbers.


## Overview
The Resume Optimizer uses Generative AI to rewrite professional experiences and summaries to align with a specific job description's language and requirements.

## Optimization Pipeline
```text
[Resume JSON] + [JD JSON] --> [Bullet Rewriter] --> [Keyword Injector] --> [Final Polish]
```

### 1. Bullet Rewriting Pipeline
- **Input**: Original bullet points from the resume.
- **Context**: Responsibilities and skills from the JD.
- **Logic**: For each bullet, the LLM is asked to:
    1. Identify a related skill in the JD.
    2. Mirror the JD's terminology (e.g., if JD says "Scalable Microservices", rewrite "Large scale apps" to "Scalable Microservices").
    3. Maintain 100% factual accuracy.

### 2. Keyword Injection
- Matches mandatory keywords from the JD that are present in the candidate's general profile but missing from the current resume text.
- Injects these naturally into the "Skills" or "Summary" sections.

### 3. Metric Enhancement
- Detects where bullets lack quantifiable data and suggests placeholders or prompts the user for specific numbers based on the JD's scope (e.g., "Led team of X developers to reduce latency by Y%").

## LLM Prompt Templates (Snippet)
```text
System: You are an expert career coach and ATS specialist.
Goal: Rewrite the following bullet points to mirror the Job Description provided.
Constraint: Use "Result-Action-Context" framework. DO NOT fabricate experience.
```

## Company-Specific Adaptation
- **Startup Mode**: Emphasizes agility, multi-tasking, and ownership.
- **Enterprise Mode**: Emphasizes scalability, compliance, and cross-functional leadership.

## Future Extensibility
- A/B testing multiple versions of the same resume against simulated ATS parsers.
