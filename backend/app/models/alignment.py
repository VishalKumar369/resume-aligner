from sqlalchemy import Column, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class AlignmentScore(Base):
    __tablename__ = "alignment_scores"

    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    jd_id = Column(UUID(as_uuid=True), ForeignKey("job_descriptions.id"), nullable=False)
    
    total_alignment_score = Column(Float, default=0.0)
    ats_score = Column(Float, default=0.0)
    
    # Detailed score components
    skill_match_score = Column(Float)
    experience_match_score = Column(Float)
    cultural_fit_score = Column(Float)
    
    analysis_data = Column(JSON) # Store feedback, missing keywords, etc.

    # Relationships
    resume = relationship("Resume", back_populates="alignment_scores")
    jd = relationship("JobDescription", back_populates="alignment_scores")
