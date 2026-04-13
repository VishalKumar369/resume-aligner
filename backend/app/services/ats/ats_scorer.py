from typing import List, Dict
from app.schemas.analytics import ATSScoreSchema

class ATSScorerService:
    @staticmethod
    async def compute_score(resume_text: str, jd_text: str) -> ATSScoreSchema:
        """
        Calculates a weighted ATS score based on:
        - Keyword density (40%)
        - Metrics presence (20%)
        - Section completeness (10%)
        - Bullet point clarity (10%)
        - Formatting best practices (20%)
        """
        # Placeholder logic for demonstration
        # In a real app, this would use NLP/LLM extraction
        
        keywords_match = 0.85
        metrics_found = 0.70
        sections_complete = 0.90
        clarity_score = 0.80
        formatting_score = 0.95
        
        weighted_score = (
            (keywords_match * 0.40) +
            (metrics_found * 0.20) +
            (sections_complete * 0.10) +
            (clarity_score * 0.10) +
            (formatting_score * 0.20)
        ) * 100

        return ATSScoreSchema(
            score=round(weighted_score, 2),
            breakdown={
                "Keywords": keywords_match * 100,
                "Metrics": metrics_found * 100,
                "Structure": sections_complete * 100,
                "Clarity": clarity_score * 100,
                "Formatting": formatting_score * 100
            },
            formatting_feedback=["Strong use of standard fonts", "Consistent date formatting"],
            content_feedback=["Add more quantifiable metrics to your recent role", "Include specific cloud provider names"]
        )
