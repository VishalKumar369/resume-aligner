from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Note(Base):
    """A personal planning note / journal entry.

    Lightweight and private to its owner: a place to write down goals, plans, and
    reflections, optionally with a target date to work towards.
    """

    __tablename__ = "notes"

    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False, default="")
    # Freeform label the user groups notes by (e.g. "Goal", "Journal", "Idea").
    category = Column(String, nullable=False, default="Note")
    # A colour accent for the card, e.g. "primary" | "success" | "warning".
    color = Column(String, nullable=False, default="primary")
    # Optional date the user is planning towards.
    target_date = Column(DateTime, nullable=True)
    is_pinned = Column(Boolean, nullable=False, default=False)
    is_completed = Column(Boolean, nullable=False, default=False)
