from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import (
    ResendVerificationRequest,
    Token,
    UserCreate,
    UserOut,
    VerifyEmailRequest,
)
from app.services.auth.email_verification import check_code, issue_code

router = APIRouter()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _token_for(user: User) -> dict:
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(user.id, expires_delta=expires),
        "token_type": "bearer",
    }


@router.get("/config")
async def auth_config():
    """Client-visible auth switches (so the UI can mirror the server)."""
    return {"email_verification_enabled": settings.EMAIL_VERIFICATION_ENABLED}


@router.post("/signup", response_model=UserOut)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(User, db)
    normalized_email = normalize_email(user_in.email)
    user = await repo.get_by_email(normalized_email)
    if user:
        raise HTTPException(status_code=400, detail="User already exists")

    obj_in = user_in.model_dump(exclude={"password"})
    obj_in["email"] = normalized_email
    obj_in["hashed_password"] = security.get_password_hash(user_in.password)
    # When verification is on the account starts unverified and must confirm an
    # OTP before it can log in; otherwise it is usable immediately.
    obj_in["email_verified"] = not settings.EMAIL_VERIFICATION_ENABLED
    created = await repo.create(obj_in=obj_in)

    if settings.EMAIL_VERIFICATION_ENABLED:
        await issue_code(db, normalized_email)
    return created


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    repo = UserRepository(User, db)
    normalized_email = normalize_email(form_data.username)
    user = await repo.get_by_email(normalized_email)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    if settings.EMAIL_VERIFICATION_ENABLED and not user.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    return _token_for(user)


@router.post("/verify-email", response_model=Token)
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    if not settings.EMAIL_VERIFICATION_ENABLED:
        raise HTTPException(status_code=400, detail="Email verification is disabled.")

    repo = UserRepository(User, db)
    user = await repo.get_by_email(payload.email)
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found.")

    # Already verified: never hand out a token without a code — send them to login.
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified. Please log in.")

    # A valid code proves ownership of the inbox, so completing it logs the user
    # in (the same person set the password at signup).
    if not await check_code(db, payload.email, payload.code):
        raise HTTPException(status_code=400, detail="Invalid or expired code.")
    user.email_verified = True
    await db.commit()
    return _token_for(user)


@router.post("/resend-verification")
async def resend_verification(payload: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    if not settings.EMAIL_VERIFICATION_ENABLED:
        raise HTTPException(status_code=400, detail="Email verification is disabled.")

    user = await UserRepository(User, db).get_by_email(payload.email)
    # Don't reveal whether the account exists; only actually send when it needs it.
    if user is not None and not user.email_verified:
        await issue_code(db, payload.email)
    return {"detail": "If that account needs verification, a new code has been sent."}
