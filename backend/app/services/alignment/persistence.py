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
            analysis_data={
                "missing_keywords": result.get("missing_keywords", []),
                "feedback": result.get("feedback", ""),
                "improvement_suggestions": result.get("improvement_suggestions", []),
            },
        )
        self.db.add(score)
        await self.db.flush()
        await self.db.refresh(score)
        return score
