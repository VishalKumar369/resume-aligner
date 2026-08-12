import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.analytics import LearningRoadmapSchema
from app.services.dashboard.analytics import DashboardAnalyticsService
from app.services.learning.roadmap_generator import LearningRoadmapService

router = APIRouter()


@router.get("/roadmap", response_model=LearningRoadmapSchema)
async def get_learning_roadmap(
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    """A learning plan built from the gaps in the user's own target roles.

    Returns an empty plan with a note when there are no gaps to close, rather
    than inventing modules.
    """
    report = await DashboardAnalyticsService().get_gap_report(db, owner_id)
    return await LearningRoadmapService().generate(report)
