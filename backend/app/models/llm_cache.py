from sqlalchemy import Column, JSON, String

from app.db.base import Base


class LLMCacheEntry(Base):
    """A stored model result, keyed by a hash of its input.

    Free-tier quotas are metered per day, so repeating a call for input already
    seen is expensive in a way normal caching is not. This is persisted rather
    than held in memory so a restart does not throw the budget away.
    """

    __tablename__ = "llm_cache"

    cache_key = Column(String, nullable=False, unique=True, index=True)
    feature = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
