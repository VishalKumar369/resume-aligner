from typing import Any, Optional
import json
from app.core.config import settings

class CacheAdapter:
    def __init__(self):
        self._cache = {} # In-memory fallback

    async def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    async def set(self, key: str, value: Any, expire: int = 3600):
        self._cache[key] = value

    async def delete(self, key: str):
        if key in self._cache:
            del self._cache[key]

# In a real app, this would return a Redis adapter if settings.USE_REDIS is True
def get_cache():
    return CacheAdapter()
