from typing import List, Dict, Any
from app.schemas.analytics import LearningRoadmapSchema

class LearningRoadmapService:
    async def generate_roadmap(self, missing_skills: List[str]) -> LearningRoadmapSchema:
        """
        Generates a week-by-week learning plan based on skill gaps.
        """
        weeks = []
        for i, skill in enumerate(missing_skills[:4], 1):
            weeks.append({
                "week": i,
                "topic": f"Mastering {skill}",
                "focus": ["Core concepts", "Hands-on project", "Best practices"]
            })
            
        return LearningRoadmapSchema(
            weeks=weeks,
            total_duration=f"{len(weeks)} Weeks",
            resources=[
                {"title": "Coursera: Cloud Infrastructure", "url": "https://coursera.org/..."},
                {"title": "Official K8s Documentation", "url": "https://kubernetes.io/docs"}
            ]
        )
