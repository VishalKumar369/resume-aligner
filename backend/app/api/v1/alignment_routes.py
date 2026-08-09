from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.analytics import AlignmentRequestSchema, AlignmentResponseSchema
from app.services.alignment.scorer import AlignmentScorerService

router = APIRouter()


@router.post("/generate", response_model=AlignmentResponseSchema)
async def generate_alignment(
    payload: AlignmentRequestSchema,
    db: AsyncSession = Depends(get_db),
):
    service = AlignmentScorerService()
    result = await service.calculate_alignment(
        resume_id=payload.resume_id, jd_id=payload.jd_id, db=db
    )
    await db.commit()
    return result
