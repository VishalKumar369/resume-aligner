"""Single-pair skill gap detection.

Delegates to the Phase 4 `SkillMatcher` so gaps, partial matches, and P1/P2/P3
priorities are derived the same way the alignment score derives them. The
previous implementation did its own lowercase set difference and attached a
hardcoded `demand_index: 92` to every gap.
"""

from typing import Any, Dict, List, Optional

from app.schemas.analytics import SkillGapSchema
from app.services.alignment.skill_matcher import SkillMatcher


class SkillGapDetectorService:
    def __init__(self, matcher: Optional[SkillMatcher] = None):
        self.matcher = matcher or SkillMatcher()

    async def detect(
        self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]
    ) -> SkillGapSchema:
        report = self.matcher.match(resume_data, jd_data)

        return SkillGapSchema(
            missing_skills=report.missing_display_names,
            partial_skills=[
                f"{item.skill} (you have {item.covered_by})" for item in report.partial
            ],
            priority_rank=[
                {
                    "skill": item.skill,
                    "priority": item.priority,
                    "importance": item.importance,
                    "weight": round(item.weight, 2),
                }
                for item in report.missing
            ],
        )

    async def detect_gaps(
        self, resume_skills: List[str], jd_skills: List[str]
    ) -> SkillGapSchema:
        """Compare bare skill lists, for callers without full structured data."""
        return await self.detect(
            {"skills": {"hard_skills": list(resume_skills), "normalized": [
                str(skill).lower() for skill in resume_skills
            ]}},
            {"requirements": {
                "mandatory_skills": list(jd_skills),
                "normalized_mandatory": [str(skill).lower() for skill in jd_skills],
            }},
        )
