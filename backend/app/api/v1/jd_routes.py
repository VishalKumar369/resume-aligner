import hashlib
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.jd import JobDescription
from app.repositories.jd_repo import JDRepository
from app.schemas.jd import JDOut, JDUploadSchema
from app.services.parsing.jd_parser import JDParserService

router = APIRouter()

# The upload page currently sends these fixed strings for every JD, so they are
# treated as "nothing supplied" and the parsed values win.
PLACEHOLDER_VALUES = {"target role", "company", "string", "untitled", "n/a", "-"}
MAX_PAGE_SIZE = 100


@router.post("/upload", response_model=JDOut)
async def upload_jd(
    jd_in: JDUploadSchema,
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    raw_text = (jd_in.raw_text or "").strip()
    if not raw_text:
        raise HTTPException(
            status_code=422,
            detail="Job description text is required. Paste the posting to continue.",
        )

    repo = JDRepository(JobDescription, db)
    content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    # The same posting pasted twice costs nothing: parsing it may spend a model
    # call, and free-tier quotas are metered per day.
    existing = await repo.get_by_content_hash(owner_id, content_hash)
    if existing is not None:
        return existing

    structured_data = await JDParserService().parse(raw_text)
    jd = await repo.create(obj_in={
        "owner_id": owner_id,
        "title": _resolve(jd_in.title, structured_data.get("role")) or "Untitled role",
        "company_name": _resolve(jd_in.company_name, structured_data.get("company")),
        "raw_text": raw_text,
        "content_hash": content_hash,
        "structured_data": structured_data,
        "url": str(jd_in.url) if jd_in.url else None,
    })
    await db.commit()
    return jd


@router.get("/list", response_model=List[JDOut])
async def list_jds(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    repo = JDRepository(JobDescription, db)
    return await repo.get_by_owner(owner_id, skip=skip, limit=limit)


@router.get("/{jd_id}", response_model=JDOut)
async def get_jd(
    jd_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    repo = JDRepository(JobDescription, db)
    jd = await repo.get(jd_id)
    if not jd or jd.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Job description not found")
    return jd


def _resolve(supplied: Optional[str], parsed: Optional[str]) -> Optional[str]:
    """Prefer a real client value, else what was parsed from the posting."""
    candidate = (supplied or "").strip()
    if candidate and candidate.lower() not in PLACEHOLDER_VALUES:
        return candidate
    return (parsed or "").strip() or None
