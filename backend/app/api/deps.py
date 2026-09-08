"""Shared route dependencies.

Until now every data route attributed its work to a single shared demo user, so
a JWT was accepted and then ignored: two accounts saw each other's resumes.
`get_current_user` makes the token decide whose data a request touches.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")
# Same scheme, but a missing token yields None instead of a 401.
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False
)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """The authenticated user, or 401."""
    user = await _user_from_token(token, db)
    if user is None:
        raise CREDENTIALS_ERROR
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(optional_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """The authenticated user if a valid token was sent, else None."""
    if not token:
        return None
    return await _user_from_token(token, db)


async def get_current_user_id(user: User = Depends(get_current_user)) -> UUID:
    return user.id


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """The signed-in user, but only if their email is in ADMIN_EMAILS; else 403."""
    if (user.email or "").strip().lower() not in settings.admin_email_set:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user


async def _user_from_token(token: Optional[str], db: AsyncSession) -> Optional[User]:
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        subject = payload.get("sub")
    except JWTError:
        return None

    if not subject:
        return None

    try:
        user_id = UUID(str(subject))
    except (ValueError, TypeError):
        return None

    user = await UserRepository(User, db).get(user_id)
    if user is None or not user.is_active:
        return None
    return user
