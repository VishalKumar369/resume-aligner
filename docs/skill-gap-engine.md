# Skill Gap Engine

## Overview
The Skill Gap Engine identifies the delta between a candidate's current capabilities and a target job's requirements.

## Logic Flow
1. **Extraction**: Get candidate skills ($S_c$) and JD required skills ($S_r$).
2. **Set Delta**: Identify $G = S_r - S_c$.
3. **Priority Ranking**:
    - **P1 (Critical)**: Mandatory skills missing with high semantic relevance to the role title.
    - **P2 (Important)**: Mandatory skills missing with medium relevance.
    - **P3 (Bonus)**: "Nice to have" skills identified in the JD.

## Weighting Logic
Skills are weighted by **Market-Demand**. We use a pre-calculated index from job market data to determine which gaps are most "expensive" for a candidate (e.g., missing "Kubernetes" is a higher priority gap than missing "Jira").

## Multi-JD Aggregation
If a user uploads multiple JDs for a single career path, the engine calculates the **Commonality Gap**—the set of skills missing across all target roles.

## Output Structure
```json
{
  "gaps": [
    {
      "skill": "Terraform",
      "priority": "P1",
      "type": "Hard Skill",
      "market_demand_percentile": 92
    }
  ],
  "market_alignment_score": 65
}
```
