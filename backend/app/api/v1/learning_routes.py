from fastapi import APIRouter, Depends
from app.schemas.analytics import LearningRoadmapSchema
from app.services.learning.roadmap_generator import LearningRoadmapService

router = APIRouter()

@router.get("/roadmap", response_model=LearningRoadmapSchema)
async def get_learning_roadmap():
    service = LearningRoadmapService()
    # In a real app, this would use the user's missing skills from DB
    return await service.generate_roadmap(["Kubernetes", "Redis", "System Design"])
