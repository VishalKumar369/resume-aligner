from sqlalchemy import Column, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class NotificationSettings(Base):
    """Per-user notification preferences.

    Kept in a dedicated 1:1 table rather than on `users` so notification toggles
    can grow over time without widening the auth-critical row. One record per
    user, created lazily with sensible defaults on first read.
    """

    __tablename__ = "notification_settings"

    # Unique FK enforces the 1:1 relationship at the database level.
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    email_alerts_on_new_matches = Column(Boolean, nullable=False, default=True)
    weekly_career_readiness_report = Column(Boolean, nullable=False, default=True)

    user = relationship("User", back_populates="notification_settings")
