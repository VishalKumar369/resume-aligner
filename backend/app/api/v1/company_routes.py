from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.get("/{companyId}/insights")
async def get_company_insights(companyId: str):
    return {
        "company_id": companyId,
        "name": "Google" if "google" in companyId.lower() else "Tech Corp",
        "tech_stack": ["Python", "Go", "Kubernetes", "GCP"],
        "culture": ["Innovation", "Scale", "Engineering Excellence"],
        "interview_tips": [
            "Focus on algorithms and data structures",
            "Be prepared to discuss system design at scale",
            "Demonstrate familiarity with GCP ecosystems"
        ],
        "openings": [
            {"title": "Senior Backend Engineer", "url": "#"},
            {"title": "Site Reliability Engineer", "url": "#"}
        ]
    }
