import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.alignment import AlignmentScore
from app.models.jd import JobDescription
from app.models.resume import Resume
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
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    await _assert_owns_pair(db, payload.resume_id, payload.jd_id, owner_id)
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
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    """Stored alignment runs, newest first."""
    repo = AlignmentRepository(AlignmentScore, db)
    rows = await repo.list_alignments(
        owner_id=owner_id,
        resume_id=resume_id,
        jd_id=jd_id,
        latest_only=latest_only,
        skip=skip,
        limit=limit,
    )

    # Batch-load the JDs and resumes these runs reference, so each row can be
    # labelled "Company - Role" without a per-row query.
    jds = await _by_id(db, JobDescription, {row.jd_id for row in rows})
    resumes = await _by_id(db, Resume, {row.resume_id for row in rows})
    return [_to_summary(row, jds.get(row.jd_id), resumes.get(row.resume_id)) for row in rows]


async def _by_id(db: AsyncSession, model, ids) -> Dict[uuid.UUID, Any]:
    ids = [i for i in ids if i is not None]
    if not ids:
        return {}
    rows = (await db.execute(select(model).where(model.id.in_(ids)))).scalars().all()
    return {row.id: row for row in rows}


@router.get("/{alignment_id}", response_model=AlignmentDetailSchema)
async def get_alignment(
    alignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    """A single stored run with its full analysis."""
    repo = AlignmentRepository(AlignmentScore, db)
    row = await repo.get(alignment_id)
    if not row or not await repo.is_owned_by(row, owner_id, db):
        raise HTTPException(status_code=404, detail="Alignment not found")
    return _to_detail(row)


async def _assert_owns_pair(db, resume_id, jd_id, owner_id) -> None:
    resume = await db.get(Resume, resume_id)
    jd = await db.get(JobDescription, jd_id)
    if not resume or not jd or resume.owner_id != owner_id or jd.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Resume or JD not found")


def _to_summary(
    row: AlignmentScore,
    jd: Optional[JobDescription] = None,
    resume: Optional[Resume] = None,
) -> AlignmentSummarySchema:
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
        # Labels are best-effort: a single-run read passes neither, and a JD may
        # carry no company name.
        company=(jd.company_name if jd else None),
        role=(jd.title if jd else None),
        resume_label=((resume.label or resume.filename) if resume else None),
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
