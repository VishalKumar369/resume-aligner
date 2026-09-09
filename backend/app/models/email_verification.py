from sqlalchemy import Column, DateTime, Integer, String

from app.db.base import Base


class EmailVerificationCode(Base):
    """A short-lived OTP for confirming an email at signup.

    One active code per email (a new request replaces the old). The code itself
    is never stored — only a salted hash — and it expires and caps attempts.
    """

    __tablename__ = "email_verification_codes"

    email = Column(String, nullable=False, index=True)
    code_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
