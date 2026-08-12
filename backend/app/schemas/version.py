from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ResumeVersionOut(BaseModel):
    id: UUID
    resume_id: UUID
    jd_id: Optional[UUID] = None
    version_number: int
    label: Optional[str] = None
    filename: str
    ats_score: Optional[float] = None
    alignment_score: Optional[float] = None
    baseline_ats_score: Optional[float] = None
    baseline_alignment_score: Optional[float] = None
    changes_applied: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OptimizeResponse(BaseModel):
    """Result of tailoring a resume to one job description."""

    version_id: UUID
    version_number: int
    label: Optional[str] = None
    filename: str

    baseline_ats_score: float
    baseline_alignment_score: float
    ats_score: float
    alignment_score: float
    ats_delta: float
    alignment_delta: float

    # Each change carries a description, and before/after text for rewrites.
    changes: List[Dict[str, Any]] = []
    # Advice for bullets that were not rewritten.
    suggestions: List[str] = []
    # Rewrites discarded for introducing facts the resume does not support.
    blocked_rewrites: List[Dict[str, str]] = []

    used_llm: bool = False
    note: Optional[str] = None
    scoring_note: Optional[str] = None

    download_docx: str
    download_pdf: str
