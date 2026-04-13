from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Resume(Base):
    __tablename__ = "resumes"

    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    s3_path = Column(String)
    raw_text = Column(String)
    structured_data = Column(JSON) # Extracted skills, exp, etc.
    
    # Relationships
    owner = relationship("User", back_populates="resumes")
    versions = relationship("ResumeVersion", back_populates="resume", cascade="all, delete-orphan")
    alignment_scores = relationship("AlignmentScore", back_populates="resume", cascade="all, delete-orphan")
