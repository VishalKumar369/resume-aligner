from typing import Optional
from sqlalchemy import select, func
from app.models.user import User
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    async def get_by_email(self, email: str) -> Optional[User]:
        normalized_email = email.strip().lower()
        query = select(self.model).where(func.lower(self.model.email) == normalized_email, self.model.is_deleted == False)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
