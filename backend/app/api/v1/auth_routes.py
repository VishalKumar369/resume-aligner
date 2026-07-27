from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.user import UserOut, UserCreate, Token
from app.repositories.user_repo import UserRepository
from app.models.user import User
from app.core import security
from app.core.config import settings

router = APIRouter()


def normalize_email(email: str) -> str:
    return email.strip().lower()


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
    return await repo.create(obj_in=obj_in)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    repo = UserRepository(User, db)
    normalized_email = normalize_email(form_data.username)
    user = await repo.get_by_email(normalized_email)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(user.id, expires_delta=access_token_expires),
        "token_type": "bearer",
    }
