import hashlib
import logging
import os
import re
import uuid
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.jd import JobDescription
from app.models.resume import Resume
from app.models.version import ResumeVersion
from app.repositories.resume_repo import ResumeRepository
from app.repositories.version_repo import ResumeVersionRepository
from app.schemas.resume import ResumeOptimizeRequest, ResumeOut
from app.schemas.version import OptimizeResponse, ResumeVersionOut
from app.services.documents.writers import LAYOUT_IDS, render_docx, render_pdf
from app.services.documents.docx_editor import docx_to_pdf, optimize_docx_in_place
from app.services.documents.keyword_highlight import compile_keyword_pattern, jd_keywords
from app.services.extraction.types import FileType
from app.services.optimization.engine import OptimizationEngine
from app.services.parsing.resume_parser import ResumeParserService
from app.services.storage.storage_adapter import get_storage

router = APIRouter()

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # matches the 5MB limit advertised in the UI
SUPPORTED_TYPES = {FileType.PDF, FileType.DOCX, FileType.TXT}
MAX_PAGE_SIZE = 100

DOWNLOAD_FORMATS = {
    "docx": ("s3_path", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "pdf": ("pdf_path", "application/pdf"),
}


@router.post("/upload", response_model=ResumeOut)
async def upload_resume(
    file: UploadFile = File(...),
    label: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.",
        )

    repo = ResumeRepository(Resume, db)
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    # Re-uploading the same file returns the existing record: no second copy on
    # disk, no repeated parse.
    existing = await repo.get_by_content_hash(owner_id, content_hash)
    if existing is not None:
        return ResumeOut.model_validate(existing).model_copy(
            update={"duplicate_of_existing": True}
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
    file_path = await storage.upload_file(BytesIO(file_bytes), file.filename)

    resume = await repo.create(obj_in={
        "owner_id": owner_id,
        "filename": file.filename,
        "label": (label or "").strip() or None,
        "s3_path": file_path,
        "content_hash": content_hash,
        "raw_text": extraction.text,
        "structured_data": structured_data,
        "extraction_meta": _extraction_meta(extraction, structured_data),
    })
    await db.commit()
    return resume


@router.get("/list", response_model=List[ResumeOut])
async def list_resumes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    repo = ResumeRepository(Resume, db)
    return await repo.get_by_owner(owner_id, skip=skip, limit=limit)


@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    repo = ResumeRepository(Resume, db)
    resume = await repo.get(resume_id)
    # A resume belonging to someone else is indistinguishable from one that
    # does not exist, so ownership is never leaked.
    if not resume or resume.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_resume(
    payload: ResumeOptimizeRequest,
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    """Tailor a resume to one job description and store it as a new version."""
    resume = await db.get(Resume, payload.resume_id)
    jd = await db.get(JobDescription, payload.jd_id)
    if not resume or not jd or resume.owner_id != owner_id or jd.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Resume or JD not found")

    parser = ResumeParserService()
    resume_data = resume.structured_data or await parser.parse(resume.raw_text or "")
    jd_data = jd.structured_data or {}

    if not resume_data.get("experience") and not (resume_data.get("skills") or {}).get("hard_skills"):
        raise HTTPException(
            status_code=422,
            detail="This resume has no readable experience or skills to optimize.",
        )

    # Layout & sections. "original" (the default for a .docx upload) keeps the
    # user's own file; any template layout — or a PDF upload — rebuilds it, and
    # only then does the section reorder/exclude apply.
    original_is_docx = (resume.filename or "").lower().endswith(".docx")
    requested_layout = (payload.layout or "").strip().lower()
    use_original = requested_layout in ("", "original") and original_is_docx
    template_layout = requested_layout if requested_layout in LAYOUT_IDS else "classic"
    section_order = None if use_original else (payload.sections or None)

    result = await OptimizationEngine(db=db).optimize(
        resume_data,
        jd_data,
        resume_text=resume.raw_text or "",
        extraction_meta=resume.extraction_meta,
        single_page=payload.page_preference == "single",
        section_order=section_order,
    )

    repo = ResumeVersionRepository(ResumeVersion, db)
    version_number = await repo.next_version_number(payload.resume_id)
    label = _version_label(jd, version_number)
    stem = _version_stem(resume.filename, version_number)

    storage = get_storage()
    docx_bytes, pdf_bytes, preserved = await _build_optimized_documents(
        resume, result, jd_data, storage,
        use_original=use_original, layout=template_layout, section_order=section_order,
    )
    if preserved:
        # In-place editing keeps the user's layout, so only the bullet rewrites
        # (and any blocked ones) are actually reflected — reordering, condensing,
        # and skill promotion are structural changes we deliberately don't make
        # to their design. Report only what the delivered file really contains.
        reflected = [
            change for change in result.changes
            if change.get("type") in ("bullet_rewritten", "rewrites_blocked")
        ]
        result.changes = [{
            "type": "format_preserved",
            "description": (
                "Kept your original resume's formatting — fonts, colours, "
                "links, and layout — and optimized only the wording."
            ),
        }] + reflected
    docx_path = await storage.upload_file(BytesIO(docx_bytes), f"{stem}.docx")
    pdf_path = await storage.upload_file(BytesIO(pdf_bytes), f"{stem}.pdf")

    version = await repo.create(obj_in={
        "resume_id": payload.resume_id,
        "jd_id": payload.jd_id,
        "version_number": version_number,
        "label": label,
        "filename": f"{stem}.docx",
        "s3_path": docx_path,
        "pdf_path": pdf_path,
        "changes_applied": result.changes,
        "optimized_data": result.optimized_data,
        "ats_score": result.ats_score,
        "alignment_score": result.alignment_score,
        "baseline_ats_score": result.baseline_ats_score,
        "baseline_alignment_score": result.baseline_alignment_score,
    })
    await db.commit()

    return OptimizeResponse(
        version_id=version.id,
        version_number=version_number,
        label=label,
        filename=version.filename,
        baseline_ats_score=result.baseline_ats_score,
        baseline_alignment_score=result.baseline_alignment_score,
        ats_score=result.ats_score,
        alignment_score=result.alignment_score,
        ats_delta=result.ats_delta,
        alignment_delta=result.alignment_delta,
        changes=result.changes,
        suggestions=result.suggestions,
        blocked_rewrites=result.rejected_rewrites,
        used_llm=result.used_llm,
        from_cache=result.from_cache,
        note=result.llm_note,
        scoring_note=result.scoring_note,
        single_page=result.single_page,
        page_count=result.page_count,
        trimmed_bullets=result.trimmed_bullets,
        single_page_fit=result.single_page_fit,
        length_note=result.length_note,
        download_docx=f"/api/v1/resume/versions/{version.id}/download?format=docx",
        download_pdf=f"/api/v1/resume/versions/{version.id}/download?format=pdf",
    )


async def _build_optimized_documents(
    resume, result, jd_data, storage, *, use_original, layout, section_order
):
    """The .docx/.pdf to deliver for an optimized resume.

    With "original" on a .docx upload, edit that file in place so the user's own
    formatting (colours, fonts, hyperlinks, layout) is preserved and only the
    rewritten bullet wording changes; the PDF is that same document converted by
    LibreOffice. Otherwise rebuild with the chosen template ``layout`` and
    ``section_order``. Either way the JD's keywords are bolded in the bullets.
    Returns (docx_bytes, pdf_bytes, format_preserved).
    """
    keyword_pattern = compile_keyword_pattern(jd_keywords(jd_data))

    if use_original and resume.s3_path:
        try:
            original = await storage.get_file_content(resume.s3_path)
            rewrites = [
                (change["before"], change["after"])
                for change in result.changes
                if change.get("before") and change.get("after")
            ]
            edited, applied, _highlighted = optimize_docx_in_place(original, rewrites, keyword_pattern)
            # Use the preserved file when the rewrites landed, or when there
            # were none to apply (nothing to change — keep the design as-is).
            if applied or not rewrites:
                pdf = docx_to_pdf(edited) or render_pdf(
                    result.optimized_data, keyword_pattern, "classic", section_order
                )
                return edited, pdf, True
        except Exception:  # noqa: BLE001 - a format edit must never fail optimize
            logger.warning(
                "In-place .docx optimization failed; using the template renderer.",
                exc_info=True,
            )
    return (
        render_docx(result.optimized_data, keyword_pattern, layout, section_order),
        render_pdf(result.optimized_data, keyword_pattern, layout, section_order),
        False,
    )


@router.get("/versions/{version_id}/download")
async def download_version(
    version_id: uuid.UUID,
    format: str = Query("docx", pattern="^(docx|pdf)$"),
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    repo = ResumeVersionRepository(ResumeVersion, db)
    version = await repo.get(version_id)
    if not version or not await repo.is_owned_by(version, owner_id, db):
        raise HTTPException(status_code=404, detail="Resume version not found")

    attribute, media_type = DOWNLOAD_FORMATS[format]
    path = getattr(version, attribute, None)
    if not path or not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=f"No {format.upper()} file stored for this version.",
        )

    stem = os.path.splitext(version.filename or "resume")[0]
    return FileResponse(path, media_type=media_type, filename=f"{stem}.{format}")


@router.get("/{resume_id}/versions", response_model=List[ResumeVersionOut])
async def list_resume_versions(
    resume_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    resume = await ResumeRepository(Resume, db).get(resume_id)
    if not resume or resume.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Resume not found")
    repo = ResumeVersionRepository(ResumeVersion, db)
    return await repo.list_for_resume(resume_id, skip=skip, limit=limit)


def _version_label(jd: JobDescription, version_number: int) -> str:
    target = " - ".join(
        part for part in (jd.company_name, jd.title) if part and str(part).strip()
    )
    return f"v{version_number} tailored for {target}" if target else f"v{version_number}"


def _version_stem(filename: Optional[str], version_number: int) -> str:
    base = os.path.splitext(os.path.basename(filename or "resume"))[0]
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._") or "resume"
    return f"{safe}_optimized_v{version_number}"


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
