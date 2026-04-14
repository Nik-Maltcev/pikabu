"""CacheService — manages parse metadata caching with TTL validation."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import ParseMetadata

logger = logging.getLogger(__name__)


class CacheService:
    """Manages cached parse metadata for topics.

    Uses the ``parse_metadata`` table to track when a topic was last parsed
    and how many posts/comments were collected.  The default TTL is taken
    from ``settings.cache_ttl_hours`` (24 h).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_cached_data(self, topic_id: int) -> ParseMetadata | None:
        """Return the cached :class:`ParseMetadata` for *topic_id*, or ``None``."""
        result = await self._session.execute(
            select(ParseMetadata).where(ParseMetadata.topic_id == topic_id)
        )
        return result.scalar_one_or_none()

    async def is_cache_valid(
        self, topic_id: int, ttl_hours: int | None = None
    ) -> bool:
        """Check whether cached data for *topic_id* is still fresh.

        Returns ``True`` when a :class:`ParseMetadata` record exists **and**
        its ``last_parsed_at`` is less than *ttl_hours* hours ago.
        """
        if ttl_hours is None:
            ttl_hours = settings.cache_ttl_hours

        meta = await self.get_cached_data(topic_id)
        if meta is None:
            return False

        now = datetime.now(timezone.utc)
        age_hours = (now - meta.last_parsed_at).total_seconds() / 3600
        return age_hours < ttl_hours

    async def update_cache(
        self,
        topic_id: int,
        posts_count: int,
        comments_count: int,
    ) -> ParseMetadata:
        """Create or update the :class:`ParseMetadata` record for *topic_id*."""
        meta = await self.get_cached_data(topic_id)
        now = datetime.now(timezone.utc)

        if meta is not None:
            meta.last_parsed_at = now
            meta.posts_count = posts_count
            meta.comments_count = comments_count
        else:
            meta = ParseMetadata(
                topic_id=topic_id,
                last_parsed_at=now,
                posts_count=posts_count,
                comments_count=comments_count,
            )
            self._session.add(meta)

        await self._session.flush()
        return meta
