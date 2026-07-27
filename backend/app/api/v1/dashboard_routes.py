from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.analytics import DashboardSummarySchema
from app.services.dashboard.analytics import DashboardAnalyticsService
import uuid

router = APIRouter()

@router.get("/summary", response_model=DashboardSummarySchema)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    # dummy_user_id for now
    dummy_user_id = uuid.uuid4()
    service = DashboardAnalyticsService()
    return await service.get_summary(dummy_user_id)
