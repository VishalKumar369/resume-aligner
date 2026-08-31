import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.analytics import LearningRoadmapSchema, SkillQuestionsSchema
from app.services.dashboard.analytics import DashboardAnalyticsService
from app.services.learning.question_bank import questions_for
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


@router.get("/questions", response_model=SkillQuestionsSchema)
async def get_skill_questions(
    skill: str = Query(..., description="Canonical skill name, e.g. 'LLM'"),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    """The interview question bank for one skill (404 if we have none).

    A query param (not a path segment) so skills with a slash — 'CI/CD' — work.
    """
    bank = questions_for(skill.strip())
    if bank is None:
        raise HTTPException(
            status_code=404,
            detail=f"No interview questions available for '{skill}' yet.",
        )
    return bank
