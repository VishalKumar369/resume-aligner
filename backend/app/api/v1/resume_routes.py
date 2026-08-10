import hashlib
import uuid
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.resume import Resume
from app.repositories.resume_repo import ResumeRepository
from app.schemas.resume import ResumeOptimizeRequest, ResumeOut
from app.services.auth.default_user import get_or_create_default_user
from app.services.extraction.types import FileType
from app.services.parsing.resume_parser import ResumeParserService
from app.services.storage.storage_adapter import get_storage

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # matches the 5MB limit advertised in the UI
SUPPORTED_TYPES = {FileType.PDF, FileType.DOCX, FileType.TXT}


@router.post("/upload", response_model=ResumeOut)
async def upload_resume(
    file: UploadFile = File(...),
    label: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.",
        )

    parser = ResumeParserService()
    extraction = parser.extract(
        file_bytes, filename=file.filename, content_type=file.content_type
    )

    # Fail loudly rather than persisting an unreadable resume that would later
    # look like a genuine 0% match.
    if extraction.file_type not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=extraction.detail
            or f"Unsupported file type '{extraction.file_type.value}'. Please upload a PDF or .docx.",
        )
    if not extraction.ok:
        raise HTTPException(
            status_code=422,
            detail=extraction.detail
            or "Could not read any text from this file. Please upload a text-based PDF or a .docx.",
        )

    structured_data = await parser.parse(extraction.text)

    storage = get_storage()
    owner_id = await get_or_create_default_user(db)
    file_path = await storage.upload_file(BytesIO(file_bytes), file.filename)

    repo = ResumeRepository(Resume, db)
    resume = await repo.create(obj_in={
        "owner_id": owner_id,
        "filename": file.filename,
        "label": (label or "").strip() or None,
        "s3_path": file_path,
        "content_hash": hashlib.sha256(file_bytes).hexdigest(),
        "raw_text": extraction.text,
        "structured_data": structured_data,
        "extraction_meta": _extraction_meta(extraction, structured_data),
    })
    await db.commit()
    return resume


@router.get("/list", response_model=List[ResumeOut])
async def list_resumes(db: AsyncSession = Depends(get_db)):
    repo = ResumeRepository(Resume, db)
    return await repo.get_multi()


@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume(resume_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = ResumeRepository(Resume, db)
    resume = await repo.get(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.post("/optimize")
async def optimize_resume(payload: ResumeOptimizeRequest):
    # The optimization engine is not implemented yet (planned phase).
    raise HTTPException(
        status_code=501,
        detail="Resume optimization is not implemented yet.",
    )


def _extraction_meta(extraction, structured_data: dict) -> dict:
    """One record of how this resume was read: text extraction, then structuring."""
    return {
        "method": extraction.method.value,
        "file_type": extraction.file_type.value,
        "page_count": extraction.page_count,
        "char_count": extraction.char_count,
        "word_count": extraction.word_count,
        "used_ocr": extraction.used_ocr,
        "confidence": extraction.confidence,
        "warnings": [warning.value for warning in extraction.warnings],
        "structuring": (structured_data or {}).get("extraction_meta", {}),
    }
