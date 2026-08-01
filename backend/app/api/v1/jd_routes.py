from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.jd import JDOut, JDUploadSchema
from app.models.jd import JobDescription
from app.repositories.jd_repo import JDRepository
from app.services.parsing.jd_parser import JDParserService
import uuid

router = APIRouter()

@router.post("/upload", response_model=JDOut)
async def upload_jd(
    jd_in: JDUploadSchema,
    db: AsyncSession = Depends(get_db)
):
    dummy_user_id = uuid.uuid4()
    parser = JDParserService()
    raw_text = jd_in.raw_text or ""
    structured_data = await parser.parse(raw_text)

    repo = JDRepository(JobDescription, db)
    jd = await repo.create(obj_in={
        "owner_id": dummy_user_id,
        "title": jd_in.title,
        "company_name": jd_in.company_name,
        "raw_text": raw_text,
        "structured_data": structured_data,
        "url": str(jd_in.url) if jd_in.url else None
    })
    await db.commit()
    return jd
