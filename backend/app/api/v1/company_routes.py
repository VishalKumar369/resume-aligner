import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.analytics import CompanyInsightsSchema, CompanyListItemSchema
from app.services.company.insights import CompanyInsightsService

router = APIRouter()


@router.get("/list", response_model=List[CompanyListItemSchema])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    """Every company the user has saved postings for, with a match summary."""
    return await CompanyInsightsService().list_companies(db, owner_id)


@router.get("/{companyId}/insights", response_model=CompanyInsightsSchema)
async def get_company_insights(
    companyId: str,
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    """What the user's saved postings say about a company.

    Only reports facts traceable to a job description the user uploaded. If none
    exist for this company there is nothing to report, so this 404s rather than
    guessing at a tech stack or culture.
    """
    insights = await CompanyInsightsService().get_insights(db, companyId, owner_id)
    if insights is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No job descriptions saved for '{companyId}'. Add a posting from "
                "this company to see insights."
            ),
        )
    return insights
