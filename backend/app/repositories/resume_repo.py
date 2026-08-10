from typing import List, Optional
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

    async def get_by_content_hash(self, owner_id: UUID, content_hash: str) -> Optional[Resume]:
        """Find a resume this owner has already uploaded with identical content.

        Lets an upload be idempotent: the same file returns the same record
        instead of writing another copy to disk and re-parsing it.
        """
        if not content_hash:
            return None

        query = (
            select(self.model)
            .where(
                self.model.owner_id == owner_id,
                self.model.content_hash == content_hash,
                self.model.is_deleted == False,
            )
            .order_by(self.model.created_at.asc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
