from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.resume import ResumeOut, ResumeUploadSchema
from app.models.resume import Resume
from app.repositories.resume_repo import ResumeRepository
from app.services.storage.storage_adapter import get_storage
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
    # In a real app, user_id would come from JWT dependency
    dummy_user_id = uuid.uuid4() 
    
    file_path = await storage.upload_file(file.file, file.filename)
    
    repo = ResumeRepository(Resume, db)
    return await repo.create(obj_in={
        "owner_id": dummy_user_id,
        "filename": file.filename,
        "s3_path": file_path,
        "label": label
    })

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
