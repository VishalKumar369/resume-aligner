from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Feedback(Base):
    """A piece of user feedback about the product.

    Can come from the public landing page (anonymous, no owner) or from a
    signed-in user's Settings page (attributed to their account).
    """

    __tablename__ = "feedback"

    # Null for anonymous landing-page feedback; set for a signed-in user.
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Optional 1–5 star rating.
    rating = Column(Integer, nullable=True)
    message = Column(String, nullable=False)
    # Optional contact email, mainly for anonymous submissions.
    email = Column(String, nullable=True)
    # Where it was sent from: "landing" | "settings".
    source = Column(String, nullable=True)
