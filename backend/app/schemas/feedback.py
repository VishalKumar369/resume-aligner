from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

_ALLOWED_SOURCES = {"landing", "settings", "app"}


class FeedbackCreate(BaseModel):
    message: str
    rating: Optional[int] = None
    email: Optional[str] = None
    source: Optional[str] = None

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Feedback message is required.")
        return cleaned

    @field_validator("rating")
    @classmethod
    def _rating_in_range(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if not 1 <= value <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        return value

    @field_validator("source")
    @classmethod
    def _known_source(cls, value: Optional[str]) -> Optional[str]:
        return value if value in _ALLOWED_SOURCES else None

    @field_validator("email")
    @classmethod
    def _clean_email(cls, value: Optional[str]) -> Optional[str]:
        cleaned = (value or "").strip()
        return cleaned or None


class FeedbackOut(BaseModel):
    id: UUID
    rating: Optional[int] = None
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
