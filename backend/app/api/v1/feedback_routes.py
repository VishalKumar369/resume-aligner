from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user_optional
from app.db.session import get_db
from app.models.feedback import Feedback
from app.models.user import User
from app.repositories.feedback_repo import FeedbackRepository
from app.schemas.feedback import FeedbackAdminOut, FeedbackCreate, FeedbackOut

router = APIRouter()

MAX_PAGE_SIZE = 200


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


@router.get("", response_model=List[FeedbackAdminOut])
async def list_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Every submission, newest first. Restricted to admins (ADMIN_EMAILS)."""
    repo = FeedbackRepository(Feedback, db)
    return await repo.list_all(skip=skip, limit=limit)
