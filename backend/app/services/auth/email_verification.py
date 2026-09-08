"""Issue and check signup OTP codes.

The code is never stored in the clear — only a SECRET_KEY-salted SHA-256 hash.
Codes expire and are attempt-capped, and issuing a new one replaces any prior
code for that email.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.email_verification import EmailVerificationCode
from app.services.email.sender import send_otp_email


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash(code: str) -> str:
    return hashlib.sha256(f"{code}:{settings.SECRET_KEY}".encode("utf-8")).hexdigest()


async def issue_code(db: AsyncSession, email: str) -> None:
    """Replace any existing code for `email`, then send the new one."""
    await db.execute(delete(EmailVerificationCode).where(EmailVerificationCode.email == email))
    code = _generate_code()
    db.add(EmailVerificationCode(
        email=email,
        code_hash=_hash(code),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        attempts=0,
    ))
    await db.commit()
    await send_otp_email(email, code)


async def check_code(db: AsyncSession, email: str, code: str) -> bool:
    """True if `code` is the current, unexpired, unexhausted code for `email`.

    Records an attempt on every call; on success the code is consumed.
    """
    row = (
        await db.execute(
            select(EmailVerificationCode)
            .where(EmailVerificationCode.email == email)
            .order_by(EmailVerificationCode.created_at.desc())
        )
    ).scalars().first()

    if row is None or row.expires_at < datetime.utcnow() or row.attempts >= settings.OTP_MAX_ATTEMPTS:
        return False

    row.attempts += 1
    matched = secrets.compare_digest(row.code_hash, _hash((code or "").strip()))
    if matched:
        await db.execute(delete(EmailVerificationCode).where(EmailVerificationCode.email == email))
    await db.commit()
    return matched
