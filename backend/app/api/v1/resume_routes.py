from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.resume import ResumeOut
from app.models.resume import Resume
from app.repositories.resume_repo import ResumeRepository
from app.services.storage.storage_adapter import get_storage
from app.services.parsing.resume_parser import ResumeParserService
from app.services.auth.default_user import get_or_create_default_user
from typing import List
import uuid

router = APIRouter()

@router.post("/upload", response_model=ResumeOut)
async def upload_resume(
    label: str = None,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    storage = get_storage()
    owner_id = await get_or_create_default_user(db)

    file_path = await storage.upload_file(file.file, file.filename)
    file_bytes = await storage.get_file_content(file_path)

    parser = ResumeParserService()
    raw_text = parser._decode_text(file_bytes, filename=file.filename, content_type=file.content_type)

    if not raw_text.strip():
        raw_text = f"[Binary or non-text content stored as file reference only for {file.filename}]"

    structured_data = await parser.parse_bytes(file_bytes)

    repo = ResumeRepository(Resume, db)
    resume = await repo.create(obj_in={
        "owner_id": owner_id,
        "filename": file.filename,
        "s3_path": file_path,
        "raw_text": raw_text,
        "structured_data": structured_data,
    })
    await db.commit()
    return resume

@router.get("/list", response_model=List[ResumeOut])
async def list_resumes(db: AsyncSession = Depends(get_db)):
    repo = ResumeRepository(Resume, db)
    return await repo.get_multi()

@router.post("/optimize")
async def optimize_resume(
    resume_id: uuid.UUID,
    jd_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    # This would call the OptimizationEngine
    return {
        "resume_id": resume_id,
        "jd_id": jd_id,
        "optimized_filename": "optimized_resume_v2.pdf",
        "status": "completed",
        "changes": ["Added Kubernetes to skills", "Rewrote bullet points for impact"]
    }
