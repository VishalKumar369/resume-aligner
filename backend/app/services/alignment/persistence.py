from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alignment import AlignmentScore


class AlignmentPersistenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_alignment(self, *, resume_id: UUID, jd_id: UUID, result: Dict[str, Any]) -> AlignmentScore:
        score = AlignmentScore(
            resume_id=resume_id,
            jd_id=jd_id,
            total_alignment_score=float(result.get("alignment_score", 0.0)),
            ats_score=float(result.get("ats_score", 0.0)),
            skill_match_score=float(result.get("skill_match_score", 0.0)),
            experience_match_score=float(result.get("experience_match_score", 0.0)),
            # The full picture is stored so the dashboard, skill-gap, and
            # learning-roadmap features can build on it without re-scoring.
            analysis_data={
                "missing_keywords": result.get("missing_keywords", []),
                "missing_skills": result.get("missing_skills", []),
                "matched_skills": result.get("matched_skills", []),
                "partial_skills": result.get("partial_skills", []),
                "breakdown": result.get("breakdown", {}),
                "component_weights": result.get("component_weights", {}),
                "ats_breakdown": result.get("ats_breakdown", {}),
                "ats_warnings": result.get("ats_warnings", []),
                "feedback": result.get("feedback", ""),
                "improvement_suggestions": result.get("improvement_suggestions", []),
                "extraction_health": result.get("extraction_health"),
            },
        )
        self.db.add(score)
        await self.db.flush()
        await self.db.refresh(score)
        return score
