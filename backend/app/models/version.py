from sqlalchemy import Column, Float, String, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    jd_id = Column(UUID(as_uuid=True), ForeignKey("job_descriptions.id"))

    label = Column(String) # e.g. "Tailored for Acme - Senior Backend Engineer"
    filename = Column(String, nullable=False)
    s3_path = Column(String) # Path to the optimized .docx
    pdf_path = Column(String) # Path to the optimized PDF
    changes_applied = Column(JSON) # List of changes made (rewritten bullets, etc.)

    # The optimized resume itself, in the same shape as Resume.structured_data,
    # so a version can be re-scored or re-exported without redoing the work.
    optimized_data = Column(JSON)

    # Scores for this variant, so before/after is recoverable per version.
    ats_score = Column(Float)
    alignment_score = Column(Float)
    baseline_ats_score = Column(Float)
    baseline_alignment_score = Column(Float)

    # Relationships
    resume = relationship("Resume", back_populates="versions")
