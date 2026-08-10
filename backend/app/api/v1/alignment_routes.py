import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.alignment import AlignmentScore
from app.repositories.alignment_repo import AlignmentRepository
from app.schemas.analytics import (
    AlignmentDetailSchema,
    AlignmentRequestSchema,
    AlignmentResponseSchema,
    AlignmentSummarySchema,
)
from app.services.alignment.scorer import AlignmentScorerService

router = APIRouter()

MAX_PAGE_SIZE = 100


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


@router.get("/list", response_model=List[AlignmentSummarySchema])
async def list_alignments(
    resume_id: Optional[uuid.UUID] = None,
    jd_id: Optional[uuid.UUID] = None,
    latest_only: bool = Query(False, description="Only the newest run per resume/JD pair"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """Stored alignment runs, newest first."""
    repo = AlignmentRepository(AlignmentScore, db)
    rows = await repo.list_alignments(
        resume_id=resume_id,
        jd_id=jd_id,
        latest_only=latest_only,
        skip=skip,
        limit=limit,
    )
    return [_to_summary(row) for row in rows]


@router.get("/{alignment_id}", response_model=AlignmentDetailSchema)
async def get_alignment(alignment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """A single stored run with its full analysis."""
    repo = AlignmentRepository(AlignmentScore, db)
    row = await repo.get(alignment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Alignment not found")
    return _to_detail(row)


def _to_summary(row: AlignmentScore) -> AlignmentSummarySchema:
    return AlignmentSummarySchema(
        id=row.id,
        resume_id=row.resume_id,
        jd_id=row.jd_id,
        # The column is total_alignment_score; the API name stays consistent
        # with the generate response.
        alignment_score=row.total_alignment_score or 0.0,
        ats_score=row.ats_score or 0.0,
        skill_match_score=row.skill_match_score,
        experience_match_score=row.experience_match_score,
        created_at=row.created_at,
    )


def _to_detail(row: AlignmentScore) -> AlignmentDetailSchema:
    analysis: Dict[str, Any] = row.analysis_data or {}
    return AlignmentDetailSchema(
        **_to_summary(row).model_dump(),
        missing_keywords=analysis.get("missing_keywords") or [],
        matched_skills=analysis.get("matched_skills") or [],
        partial_skills=analysis.get("partial_skills") or [],
        missing_skills=analysis.get("missing_skills") or [],
        breakdown=analysis.get("breakdown") or {},
        component_weights=analysis.get("component_weights") or {},
        ats_breakdown=analysis.get("ats_breakdown") or {},
        ats_warnings=analysis.get("ats_warnings") or [],
        feedback=analysis.get("feedback") or "",
        improvement_suggestions=analysis.get("improvement_suggestions") or [],
        extraction_health=analysis.get("extraction_health"),
    )
