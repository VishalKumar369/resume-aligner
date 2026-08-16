from uuid import UUID

from sqlalchemy import select

from app.models.settings import NotificationSettings
from app.repositories.base import BaseRepository


class NotificationSettingsRepository(BaseRepository[NotificationSettings]):
    async def get_by_user(self, user_id: UUID) -> NotificationSettings | None:
        query = select(self.model).where(
            self.model.user_id == user_id,
            self.model.is_deleted == False,  # noqa: E712
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: UUID) -> NotificationSettings:
        """Return the user's settings, creating a defaults row on first access.

        Preferences are created lazily so existing accounts don't need a
        backfill; the model defaults define the initial toggle state.
        """
        existing = await self.get_by_user(user_id)
        if existing is not None:
            return existing
        return await self.create(obj_in={"user_id": user_id})
