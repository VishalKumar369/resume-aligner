from typing import List

from sqlalchemy import select

from app.models.feedback import Feedback
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[Feedback]):
    """Product feedback. Create from any client; read is admin-only."""

    async def list_all(self, *, skip: int = 0, limit: int = 200) -> List[Feedback]:
        """Every submission, newest first — for the admin inbox."""
        query = (
            select(self.model)
            .where(self.model.is_deleted == False)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
