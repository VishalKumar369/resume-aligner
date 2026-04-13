# Alignment Engine

## Overview
The Alignment Engine calculates the semantic and structural "fit" between a specific Resume and a Job Description.

## Alignment Formula
The score is a weighted average of multiple sub-scores:

$$ \text{Total Score} = (w_1 \cdot S) + (w_2 \cdot P) + (w_3 \cdot R) + (w_4 \cdot T) + (w_5 \cdot L) $$

| Component | Weight ($w$) | Description |
| :--- | :--- | :--- |
| **Skill Match (S)** | 0.40 | Overlap between resume skills and JD mandatory skills |
| **Project Match (P)** | 0.20 | Relevance of listed projects to JD industry/scope |
| **Responsibility (R)** | 0.20 | Semantic similarity between previous roles and target role |
| **Tool Match (T)** | 0.10 | Specific tool/software overlap |
| **Seniority/Level (L)** | 0.10 | Years of experience and level (Junior vs Lead) |

## Logic Components

### 1. Skill Similarity
Uses a Jaccard Similarity approach for exact keyword matches and Cosine Similarity for semantic matches (e.g., "SQL" vs "PostgreSQL").

### 2. Seniority Match
Extracted "Years of Experience" (YoE) from the resume is compared against the JD requirement.
- $YoE_{resume} \ge YoE_{jd} \Rightarrow 1.0$
- $YoE_{resume} < YoE_{jd} \Rightarrow \text{Penalty calculation}$

### 3. Responsibility Similarity
Uses LLM to evaluate if the depth of responsibility in past roles aligns with the target role's expectations.

## API Usage
Accessed via: `POST /alignment/generate`

## Future Extensibility
- **Industry Bias**: Adding specific weights for niche industries like MedTech or FinTech.
- **Entity Graph**: Using a knowledge graph to understand that "PyTorch" is a subset of "Deep Learning".
