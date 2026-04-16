from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.jd import JDOut, JDUploadSchema
from app.models.jd import JobDescription
from app.repositories.jd_repo import JDRepository
import uuid

router = APIRouter()

@router.post("/upload", response_model=JDOut)
async def upload_jd(
    jd_in: JDUploadSchema,
    db: AsyncSession = Depends(get_db)
):
    # Dummy user_id for now
    dummy_user_id = uuid.uuid4()
    repo = JDRepository(JobDescription, db)
    return await repo.create(obj_in={
        "owner_id": dummy_user_id,
        "title": jd_in.title,
        "company_name": jd_in.company_name,
        "raw_text": jd_in.raw_text,
        "url": str(jd_in.url) if jd_in.url else None
    })
