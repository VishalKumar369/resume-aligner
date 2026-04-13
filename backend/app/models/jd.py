from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class JobDescription(Base):
    __tablename__ = "job_descriptions"

    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    company_name = Column(String)
    raw_text = Column(String)
    structured_data = Column(JSON) # Parsed requirements, keywords, etc.
    url = Column(String)

    # Relationships
    owner = relationship("User", back_populates="job_descriptions")
    alignment_scores = relationship("AlignmentScore", back_populates="jd", cascade="all, delete-orphan")
