from typing import List
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume
from app.models.version import ResumeVersion
from app.repositories.base import BaseRepository


class ResumeVersionRepository(BaseRepository[ResumeVersion]):
    async def next_version_number(self, resume_id: UUID) -> int:
        """Version numbers count from 1 per resume, including deleted ones.

        Reusing a number after a delete would make two different documents share
        a name in the user's history.
        """
        query = select(func.max(self.model.version_number)).where(
            self.model.resume_id == resume_id
        )
        result = await self.db.execute(query)
        return int(result.scalar() or 0) + 1

    async def is_owned_by(
        self, version: ResumeVersion, owner_id: UUID, db: AsyncSession
    ) -> bool:
        """A version inherits ownership from the resume it was tailored from."""
        resume = await db.get(Resume, version.resume_id)
        return resume is not None and resume.owner_id == owner_id

    async def list_for_resume(
        self, resume_id: UUID, skip: int = 0, limit: int = 50
    ) -> List[ResumeVersion]:
        query = (
            select(self.model)
            .where(self.model.resume_id == resume_id, self.model.is_deleted == False)
            .order_by(self.model.version_number.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
