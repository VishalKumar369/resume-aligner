from sqlalchemy import Column, String, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    jd_id = Column(UUID(as_uuid=True), ForeignKey("job_descriptions.id"))
    
    filename = Column(String, nullable=False)
    s3_path = Column(String) # Path to the optimized PDF/Docx
    changes_applied = Column(JSON) # List of changes made (rewritten bullets, etc.)
    
    # Relationships
    resume = relationship("Resume", back_populates="versions")
