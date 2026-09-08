from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_optional
from app.db.session import get_db
from app.models.feedback import Feedback
from app.models.user import User
from app.repositories.feedback_repo import FeedbackRepository
from app.schemas.feedback import FeedbackCreate, FeedbackOut

router = APIRouter()


@router.post("", response_model=FeedbackOut, status_code=201)
async def submit_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Record a piece of feedback.

    Accepts anonymous submissions (from the landing page); when a valid token is
    sent, the feedback is attributed to that account.
    """
    data = payload.model_dump()
    if user is not None:
        data["owner_id"] = user.id
        data["email"] = data.get("email") or user.email

    repo = FeedbackRepository(Feedback, db)
    feedback = await repo.create(obj_in=data)
    await db.commit()
    return feedback
