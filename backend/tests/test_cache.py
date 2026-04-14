"""Tests for CacheService — mocked DB session."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.database import ParseMetadata
from app.services.cache import CacheService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_meta(topic_id: int = 1, hours_ago: float = 1, posts: int = 10, comments: int = 50):
    """Create a mock ParseMetadata object."""
    obj = MagicMock(spec=ParseMetadata)
    obj.id = 1
    obj.topic_id = topic_id
    obj.last_parsed_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    obj.posts_count = posts
    obj.comments_count = comments
    return obj


def _session_returning(meta):
    """Build an AsyncMock session whose execute() returns *meta*."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = meta
    session.execute = AsyncMock(return_value=mock_result)
    return session


# ---------------------------------------------------------------------------
# get_cached_data
# ---------------------------------------------------------------------------

class TestGetCachedData:
    @pytest.mark.asyncio
    async def test_returns_metadata_when_exists(self):
        meta = _make_meta(topic_id=1)
        session = _session_returning(meta)
        svc = CacheService(session)

        result = await svc.get_cached_data(1)

        assert result is meta
        assert result.topic_id == 1

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self):
        session = _session_returning(None)
        svc = CacheService(session)

        result = await svc.get_cached_data(999)

        assert result is None


# ---------------------------------------------------------------------------
# is_cache_valid
# ---------------------------------------------------------------------------

class TestIsCacheValid:
    @pytest.mark.asyncio
    async def test_valid_when_fresh(self):
        meta = _make_meta(hours_ago=1)
        session = _session_returning(meta)
        svc = CacheService(session)

        assert await svc.is_cache_valid(1) is True

    @pytest.mark.asyncio
    async def test_invalid_when_stale(self):
        meta = _make_meta(hours_ago=25)
        session = _session_returning(meta)
        svc = CacheService(session)

        assert await svc.is_cache_valid(1) is False

    @pytest.mark.asyncio
    async def test_invalid_when_no_record(self):
        session = _session_returning(None)
        svc = CacheService(session)

        assert await svc.is_cache_valid(1) is False

    @pytest.mark.asyncio
    async def test_custom_ttl_valid(self):
        meta = _make_meta(hours_ago=5)
        session = _session_returning(meta)
        svc = CacheService(session)

        assert await svc.is_cache_valid(1, ttl_hours=6) is True

    @pytest.mark.asyncio
    async def test_custom_ttl_invalid(self):
        meta = _make_meta(hours_ago=5)
        session = _session_returning(meta)
        svc = CacheService(session)

        assert await svc.is_cache_valid(1, ttl_hours=4) is False

    @pytest.mark.asyncio
    async def test_exactly_at_boundary_is_invalid(self):
        """Cache aged exactly ttl_hours should be invalid (< not <=)."""
        meta = _make_meta(hours_ago=24)
        session = _session_returning(meta)
        svc = CacheService(session)

        assert await svc.is_cache_valid(1, ttl_hours=24) is False


# ---------------------------------------------------------------------------
# update_cache
# ---------------------------------------------------------------------------

class TestUpdateCache:
    @pytest.mark.asyncio
    async def test_creates_new_record(self):
        session = _session_returning(None)
        svc = CacheService(session)

        result = await svc.update_cache(topic_id=1, posts_count=42, comments_count=100)

        assert result.topic_id == 1
        assert result.posts_count == 42
        assert result.comments_count == 100
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_updates_existing_record(self):
        existing = _make_meta(topic_id=1, posts=10, comments=50)
        session = _session_returning(existing)
        svc = CacheService(session)

        result = await svc.update_cache(topic_id=1, posts_count=99, comments_count=200)

        assert result is existing
        assert result.posts_count == 99
        assert result.comments_count == 200
        session.add.assert_not_called()
        session.flush.assert_awaited_once()
