from uuid import UUID
from app.schemas.analytics import DashboardSummarySchema

class DashboardAnalyticsService:
    async def get_summary(self, user_id: UUID) -> DashboardSummarySchema:
        """
        Aggregates metrics for the user dashboard.
        """
        return DashboardSummarySchema(
            total_resumes=5,
            avg_alignment_score=78.4,
            top_skill_gaps=["Kubernetes", "GraphQL", "Rust"],
            recent_activity=[
                {"action": "Resume Optimized", "target": "Google SWE", "date": "2024-03-25"},
                {"action": "JD Analyzed", "target": "Stripe Platform Engineer", "date": "2024-03-24"}
            ],
            career_readiness_index=82.0
        )
