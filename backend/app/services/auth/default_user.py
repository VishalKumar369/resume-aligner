from sqlalchemy.ext.asyncio import AsyncSession
from app.core import security
from app.models.user import User
from app.repositories.user_repo import UserRepository


DEFAULT_EMAIL = "demo@resume-aligner.local"
DEFAULT_PASSWORD = "demo123"
DEFAULT_NAME = "Demo User"


async def get_or_create_default_user(db: AsyncSession):
    repo = UserRepository(User, db)
    user = await repo.get_by_email(DEFAULT_EMAIL)
    if user:
        return user.id

    created = await repo.create(
        obj_in={
            "email": DEFAULT_EMAIL,
            "hashed_password": security.get_password_hash(DEFAULT_PASSWORD),
            "full_name": DEFAULT_NAME,
            "is_active": True,
            "is_superuser": False,
        }
    )
    return created.id
