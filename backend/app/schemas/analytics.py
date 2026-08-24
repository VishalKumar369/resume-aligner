from datetime import datetime
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
    # Identifies the stored run, so a client can fetch it back later.
    alignment_id: Optional[UUID] = None
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

class AlignmentSummarySchema(BaseModel):
    """A stored run, as listed. Scores only - enough for a table or a trend."""
    id: UUID
    resume_id: UUID
    jd_id: UUID
    alignment_score: float
    ats_score: float
    skill_match_score: Optional[float] = None
    experience_match_score: Optional[float] = None
    created_at: datetime
    # Labels for rendering a readable list. Populated by the list endpoint from
    # the run's JD and resume; absent (None) on single-run reads.
    company: Optional[str] = None
    role: Optional[str] = None
    resume_label: Optional[str] = None

class AlignmentDetailSchema(AlignmentSummarySchema):
    """A stored run with the full analysis, from GET /alignment/{id}."""
    missing_keywords: List[str] = []
    matched_skills: List[str] = []
    partial_skills: List[Dict[str, Any]] = []
    missing_skills: List[Dict[str, Any]] = []
    breakdown: Dict[str, float] = {}
    component_weights: Dict[str, float] = {}
    ats_breakdown: Dict[str, float] = {}
    ats_warnings: List[str] = []
    feedback: str = ""
    improvement_suggestions: List[str] = []
    extraction_health: Optional[ExtractionHealthSchema] = None

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
    modules: List[Dict[str, Any]] = []
    # Alias of `modules`, kept for the original contract.
    weeks: List[Dict[str, Any]] = []
    total_duration: str
    total_modules: int = 0
    resources: List[Dict[str, str]] = []
    skills_covered: List[str] = []
    jds_considered: int = 0
    note: Optional[str] = None

class InterviewProbabilitySchema(BaseModel):
    """A heuristic band, with its basis stated rather than implied."""
    band: str
    score: float
    basis: str
    caveat: str

class DashboardSummarySchema(BaseModel):
    totals: Dict[str, int] = {}
    total_resumes: int
    avg_alignment_score: float
    best_alignment_score: float = 0.0
    avg_ats_score: float = 0.0
    best_ats_score: float = 0.0
    career_readiness_index: float
    interview_probability: Optional[InterviewProbabilitySchema] = None
    top_skill_gaps: List[str]
    skill_gap_detail: List[Dict[str, Any]] = []
    partial_skills: List[Dict[str, Any]] = []
    readiness_trend: List[Dict[str, Any]] = []
    top_company_matches: List[Dict[str, Any]] = []
    recent_activity: List[Dict[str, Any]]
    recommended_improvements: List[Dict[str, str]] = []
    # False when the user has no alignment runs yet, so the UI can show an
    # empty state instead of a wall of zeros.
    has_data: bool = False

class CompanyListItemSchema(BaseModel):
    """A card for the Company Intelligence index.

    `named` is False for a posting with no parsed company; it then carries
    jd/resume/alignment ids so the client links straight to that analysis.
    """
    company_id: str
    company: str
    named: bool = True
    jd_id: Optional[str] = None
    resume_id: Optional[str] = None
    alignment_id: Optional[str] = None
    jd_count: int
    roles: List[str] = []
    demanded_skills: List[str] = []
    your_best_alignment: Optional[float] = None
    your_average_alignment: Optional[float] = None
    gap_count: int = 0
    last_activity: Optional[str] = None

class CompanyInsightsSchema(BaseModel):
    company_id: str
    company: str
    jd_count: int
    roles: List[str] = []
    seniority_levels: List[str] = []
    locations: List[str] = []
    work_modes: List[str] = []
    employment_types: List[str] = []
    demanded_skills: List[str] = []
    preferred_skills: List[str] = []
    your_best_alignment: Optional[float] = None
    your_average_alignment: Optional[float] = None
    your_gaps_here: List[Dict[str, Any]] = []
    postings: List[Dict[str, Any]] = []
    source: str
