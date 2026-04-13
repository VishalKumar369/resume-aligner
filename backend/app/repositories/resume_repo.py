from typing import List
from uuid import UUID
from sqlalchemy import select
from app.models.resume import Resume
from app.repositories.base import BaseRepository

class ResumeRepository(BaseRepository[Resume]):
    async def get_by_owner(self, owner_id: UUID, skip: int = 0, limit: int = 100) -> List[Resume]:
        query = (
            select(self.model)
            .where(self.model.owner_id == owner_id, self.model.is_deleted == False)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
