from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    # Aspirational role the user is targeting; drives settings/profile display.
    target_role = Column(String)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    # Whether the account's email has been confirmed via an OTP. Only enforced
    # when EMAIL_VERIFICATION_ENABLED is on; existing rows are backfilled true.
    email_verified = Column(Boolean(), default=False, nullable=False, server_default="true")

    # Relationships
    resumes = relationship("Resume", back_populates="owner", cascade="all, delete-orphan")
    job_descriptions = relationship("JobDescription", back_populates="owner", cascade="all, delete-orphan")
    # 1:1 preferences row, created lazily on first read (see NotificationSettingsRepository).
    notification_settings = relationship(
        "NotificationSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
