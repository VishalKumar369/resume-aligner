"""Schemas for the account settings surface (`/me`).

Reads are aggregated into a single `MeOut` payload so the settings page loads in
one round-trip; writes are split per concern (`ProfileUpdate`,
`NotificationUpdate`) so each section sends only its own fields and cannot
clobber the others.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# ------------------------------------------------------------------ profile

class ProfileOut(BaseModel):
    full_name: Optional[str] = None
    email: EmailStr
    target_role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    """Partial profile edit. Email is intentionally omitted: changing the login
    identity needs a verification flow, so it stays read-only here."""

    full_name: Optional[str] = None
    target_role: Optional[str] = None

    @field_validator("full_name", mode="before")
    @classmethod
    def normalize_full_name(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v = v.strip()
            return " ".join(word.capitalize() for word in v.split()) if v else None
        return v

    @field_validator("target_role", mode="before")
    @classmethod
    def normalize_target_role(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


# ------------------------------------------------------------- notifications

class NotificationOut(BaseModel):
    email_alerts_on_new_matches: bool = True
    weekly_career_readiness_report: bool = True

    model_config = ConfigDict(from_attributes=True)


class NotificationUpdate(BaseModel):
    """Partial toggle update; unset fields are left unchanged."""

    email_alerts_on_new_matches: Optional[bool] = None
    weekly_career_readiness_report: Optional[bool] = None


# --------------------------------------------------------------- aggregates

class AccountMeta(BaseModel):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeOut(BaseModel):
    """Everything the settings page needs, in one response."""

    profile: ProfileOut
    notifications: NotificationOut
    account: AccountMeta


# ------------------------------------------------------------- account ops

class DeleteAccountIn(BaseModel):
    """Destructive action: re-confirm the current password before proceeding."""

    password: str
