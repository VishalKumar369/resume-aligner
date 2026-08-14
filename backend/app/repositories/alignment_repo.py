from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alignment import AlignmentScore
from app.models.resume import Resume
from app.repositories.base import BaseRepository


class AlignmentRepository(BaseRepository[AlignmentScore]):
    """Reads back stored alignment runs.

    Every generate appends a row, so a resume/JD pair accumulates history and
    score movement over time stays recoverable.
    """

    async def list_alignments(
        self,
        *,
        owner_id: Optional[UUID] = None,
        resume_id: Optional[UUID] = None,
        jd_id: Optional[UUID] = None,
        latest_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[AlignmentScore]:
        query = select(self.model).where(self.model.is_deleted == False)

        if owner_id is not None:
            query = query.where(self.model.resume_id.in_(self._owned_resume_ids(owner_id)))
        if resume_id is not None:
            query = query.where(self.model.resume_id == resume_id)
        if jd_id is not None:
            query = query.where(self.model.jd_id == jd_id)

        if not latest_only:
            query = (
                query.order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(query)
            return list(result.scalars().all())

        # One row per resume/JD pair: DISTINCT ON needs the deduplicated columns
        # to lead the ORDER BY, so the newest-first sort is applied afterwards.
        query = query.order_by(
            self.model.resume_id,
            self.model.jd_id,
            self.model.created_at.desc(),
        ).distinct(self.model.resume_id, self.model.jd_id)

        result = await self.db.execute(query)
        rows = sorted(
            result.scalars().all(),
            key=lambda row: row.created_at,
            reverse=True,
        )
        return rows[skip: skip + limit]

    def _owned_resume_ids(self, owner_id: UUID):
        """Alignments have no owner column; they inherit it from their resume."""
        return select(Resume.id).where(
            Resume.owner_id == owner_id, Resume.is_deleted == False
        )

    async def is_owned_by(
        self, row: AlignmentScore, owner_id: UUID, db: AsyncSession
    ) -> bool:
        resume = await db.get(Resume, row.resume_id)
        return resume is not None and resume.owner_id == owner_id

    async def get_latest_for_pair(
        self, resume_id: UUID, jd_id: UUID
    ) -> Optional[AlignmentScore]:
        query = (
            select(self.model)
            .where(
                self.model.resume_id == resume_id,
                self.model.jd_id == jd_id,
                self.model.is_deleted == False,
            )
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
