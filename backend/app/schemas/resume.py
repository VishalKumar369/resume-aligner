from datetime import datetime
from typing import Any, Dict, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class ResumeBase(BaseModel):
    filename: str
    label: Optional[str] = None

class ResumeCreate(ResumeBase):
    pass

class ResumeUpdate(ResumeBase):
    label: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None

class ResumeOut(ResumeBase):
    id: UUID
    owner_id: UUID
    s3_path: Optional[str] = None
    created_at: datetime
    structured_data: Optional[Dict[str, Any]] = None
    extraction_meta: Optional[Dict[str, Any]] = None
    # True when an upload matched a resume already stored, so the existing
    # record was returned instead of writing a second copy.
    duplicate_of_existing: bool = False

    model_config = ConfigDict(from_attributes=True)

class ResumeUploadSchema(BaseModel):
    label: Optional[str] = None
    # file is handled by FastAPI UploadFile

class ResumeOptimizeRequest(BaseModel):
    resume_id: UUID
    jd_id: UUID
    focus_area: Optional[str] = None
    # "single" condenses the resume to fit one page (quantity trimmed, the most
    # job-relevant content kept); "multi" leaves it at its natural length.
    page_preference: Literal["single", "multi"] = "single"
