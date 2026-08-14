import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.analytics import DashboardSummarySchema
from app.services.dashboard.analytics import DashboardAnalyticsService

router = APIRouter()


@router.get("/summary", response_model=DashboardSummarySchema)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    """Aggregated career metrics, computed from the user's own stored data.

    Ownership is still the shared demo user, so this covers everything stored;
    per-user scoping arrives with real authentication.
    """
    service = DashboardAnalyticsService()
    return await service.get_summary(db, owner_id)
