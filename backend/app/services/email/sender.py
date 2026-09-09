"""Send transactional email — currently just the signup OTP.

If SMTP is configured (SMTP_HOST set) the code is emailed; otherwise it is
logged to the server console, so the whole flow can be tested in development
without an email account.
"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_otp_email(to_email: str, code: str) -> None:
    subject = f"Your {settings.PROJECT_NAME} verification code"
    body = (
        f"Your verification code is: {code}\n\n"
        f"It expires in {settings.OTP_EXPIRE_MINUTES} minutes. "
        "If you didn't request this, you can ignore this email."
    )

    if not settings.SMTP_HOST:
        # Development fallback — no email account needed to test.
        logger.info("[email-verification] OTP for %s: %s  (SMTP not configured)", to_email, code)
        return

    def _send() -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.SMTP_FROM or settings.SMTP_USER or "no-reply@localhost"
        message["To"] = to_email
        message.set_content(body)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)

    try:
        await asyncio.to_thread(_send)
    except Exception as exc:  # noqa: BLE001 - delivery must never crash signup
        logger.warning("Failed to email the OTP to %s: %s", to_email, exc)
        # Still surface the code in the log so a dev/test run isn't blocked.
        logger.info("[email-verification] OTP for %s: %s  (send failed)", to_email, code)
