from sqlalchemy import Column, String, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class SkillGap(Base):
    __tablename__ = "skill_gaps"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    missing_skills = Column(JSON) # List of skills
    priority_skills = Column(JSON) # Skills found in multiple JDs
    
    # Relationships
    user = relationship("User")

class LearningPath(Base):
    __tablename__ = "learning_paths"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    roadmap_data = Column(JSON) # Weekly goals, resources, etc.
    progress_percentage = Column(Float, default=0.0)
    
    # Relationships
    user = relationship("User")

class DashboardSnapshot(Base):
    __tablename__ = "dashboard_snapshots"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    snapshot_data = Column(JSON) # Aggregated metrics for fast frontend loading
    
    # Relationships
    user = relationship("User")
