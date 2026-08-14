"""Persistent cache for model results.

Keyed on a hash of the exact input, so re-running an analysis on unchanged
material costs nothing. That matters more than usual here: free-tier quotas are
metered per day, not per minute, so a wasted call is gone until tomorrow.

Stored in the database rather than memory so a restart does not discard the
day's budget.
"""

import hashlib
import json
import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_cache import LLMCacheEntry

logger = logging.getLogger(__name__)


def cache_key(feature: str, *parts: Any) -> str:
    """A stable key for a feature and its inputs."""
    payload = json.dumps(
        [feature, *[part if isinstance(part, (str, int, float)) else str(part) for part in parts]],
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LLMCache:
    def __init__(self, db: Optional[AsyncSession]):
        self.db = db

    async def get(self, key: str) -> Optional[Any]:
        if self.db is None:
            return None
        try:
            result = await self.db.execute(
                select(LLMCacheEntry).where(
                    LLMCacheEntry.cache_key == key,
                    LLMCacheEntry.is_deleted == False,
                )
            )
            entry = result.scalar_one_or_none()
        except Exception as exc:  # noqa: BLE001 - a cache miss must never fail the request
            logger.warning("LLM cache read failed: %s", exc)
            return None

        return entry.payload if entry else None

    async def put(self, key: str, feature: str, payload: Any) -> None:
        if self.db is None:
            return
        try:
            existing = await self.get(key)
            if existing is not None:
                return
            self.db.add(LLMCacheEntry(cache_key=key, feature=feature, payload=payload))
            await self.db.flush()
        except Exception as exc:  # noqa: BLE001 - caching is best effort
            logger.warning("LLM cache write failed: %s", exc)
