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

class MissingSkillSchema(BaseModel):
    skill: str
    importance: str   # mandatory | preferred
    priority: str     # P1 critical | P2 important | P3 bonus
    weight: float

class PartialSkillSchema(BaseModel):
    skill: str
    covered_by: Optional[str] = None
    category: Optional[str] = None

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

    # Added in Phase 4. Existing fields keep their meaning so the current UI
    # keeps working; these expose how the score was reached.
    breakdown: Dict[str, float] = {}
    component_weights: Dict[str, float] = {}
    matched_skills: List[str] = []
    partial_skills: List[PartialSkillSchema] = []
    missing_skills: List[MissingSkillSchema] = []
    ats_breakdown: Dict[str, float] = {}
    ats_warnings: List[str] = []

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
