from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.analytics import AlignmentResponseSchema
from app.services.alignment.scorer import AlignmentScorerService
import uuid

router = APIRouter()

@router.post("/generate", response_model=AlignmentResponseSchema)
async def generate_alignment(
    resume_id: uuid.UUID,
    jd_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    service = AlignmentScorerService()
    return await service.calculate_alignment(resume_id, jd_id)
