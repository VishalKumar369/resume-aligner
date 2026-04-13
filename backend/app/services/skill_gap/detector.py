from typing import List, Dict, Any
from app.schemas.analytics import SkillGapSchema

class SkillGapDetectorService:
    async def detect_gaps(self, resume_skills: List[str], jd_skills: List[str]) -> SkillGapSchema:
        """
        Compares resume skills against JD requirements to identify gaps.
        """
        resume_set = set(s.lower() for s in resume_skills)
        jd_set = set(s.lower() for s in jd_skills)
        
        missing = list(jd_set - resume_set)
        
        # Priority ranking based on JD frequency (simulated)
        priority = [
            {"skill": s, "priority": "High", "demand_index": 92}
            for s in missing[:2]
        ]
        
        return SkillGapSchema(
            missing_skills=missing,
            partial_skills=["Python (Advanced) vs Python (Expert)"],
            priority_rank=priority
        )
