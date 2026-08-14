from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from app.models.jd import JobDescription
from app.repositories.base import BaseRepository

class JDRepository(BaseRepository[JobDescription]):
    async def get_by_owner(self, owner_id: UUID, skip: int = 0, limit: int = 100) -> List[JobDescription]:
        query = (
            select(self.model)
            .where(self.model.owner_id == owner_id, self.model.is_deleted == False)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_content_hash(self, owner_id: UUID, content_hash: str) -> Optional[JobDescription]:
        """Find a posting this owner already saved with identical text."""
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
