from typing import List
from uuid import UUID

from sqlalchemy import select

from app.models.note import Note
from app.repositories.base import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """Personal notes, always scoped to their owner."""

    async def list_by_owner(
        self, owner_id: UUID, *, skip: int = 0, limit: int = 200
    ) -> List[Note]:
        """A user's notes: pinned first, then newest."""
        query = (
            select(self.model)
            .where(self.model.owner_id == owner_id, self.model.is_deleted == False)
            .order_by(self.model.is_pinned.desc(), self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
