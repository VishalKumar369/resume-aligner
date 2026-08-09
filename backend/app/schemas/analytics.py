from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class AlignmentRequestSchema(BaseModel):
    resume_id: UUID
    jd_id: UUID

class ExtractionHealthSchema(BaseModel):
    """Tells the caller whether a low score reflects a weak match or a failed parse."""
    resume_ok: bool = True
    jd_ok: bool = True
    warnings: List[str] = []

class AlignmentResponseSchema(BaseModel):
    resume_id: UUID
    jd_id: UUID
    alignment_score: float
    ats_score: float
    skill_match_score: float
    experience_match_score: float
    missing_keywords: List[str]
    feedback: str
    improvement_suggestions: List[str]
    extraction_health: Optional[ExtractionHealthSchema] = None

    model_config = ConfigDict(from_attributes=True)

class ATSScoreSchema(BaseModel):
    score: float
    breakdown: Dict[str, float]
    formatting_feedback: List[str]
    content_feedback: List[str]

class SkillGapSchema(BaseModel):
    missing_skills: List[str]
    partial_skills: List[str]
    priority_rank: List[Dict[str, Any]]

class LearningRoadmapSchema(BaseModel):
    weeks: List[Dict[str, Any]]
    total_duration: str
    resources: List[Dict[str, str]]

class DashboardSummarySchema(BaseModel):
    total_resumes: int
    avg_alignment_score: float
    top_skill_gaps: List[str]
    recent_activity: List[Dict[str, Any]]
    career_readiness_index: float
