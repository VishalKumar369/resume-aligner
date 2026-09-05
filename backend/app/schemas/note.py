from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

# Colour accents the UI knows how to render.
_ALLOWED_COLORS = {"primary", "accent", "success", "warning", "error"}


class NoteBase(BaseModel):
    title: str
    content: str = ""
    category: str = "Note"
    color: str = "primary"
    target_date: Optional[datetime] = None
    is_pinned: bool = False
    is_completed: bool = False

    @field_validator("color")
    @classmethod
    def _known_color(cls, value: str) -> str:
        return value if value in _ALLOWED_COLORS else "primary"

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Title is required.")
        return cleaned


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    """All fields optional — only what's sent is changed."""
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    target_date: Optional[datetime] = None
    is_pinned: Optional[bool] = None
    is_completed: Optional[bool] = None

    @field_validator("color")
    @classmethod
    def _known_color(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value if value in _ALLOWED_COLORS else "primary"

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Title cannot be blank.")
        return cleaned


class NoteOut(NoteBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
