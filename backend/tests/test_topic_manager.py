"""Tests for TopicManager — mocked HTTP, real parsing logic."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import httpx

from app.services.topic_manager import TopicManager, TopicManagerError, filter_topics


# ---------------------------------------------------------------------------
# Sample HTML fixtures
# ---------------------------------------------------------------------------

SAMPLE_COMMUNITIES_HTML = """
<html><body>
<div class="communities-item" data-community-id="science">
  <a href="/community/science">
    <span class="communities-item__title">Наука</span>
  </a>
  <span class="communities-item__subscribers">12 345 подписчиков</span>
</div>
<div class="communities-item" data-community-id="gaming">
  <a href="/community/gaming">
    <span class="communities-item__title">Игры</span>
  </a>
  <span class="communities-item__subscribers">67890</span>
</div>
<div class="communities-item" data-community-id="no-subs">
  <a href="/community/no-subs">
    <span class="communities-item__title">Без подписчиков</span>
  </a>
</div>
</body></html>
"""

EMPTY_HTML = "<html><body><p>Nothing here</p></body></html>"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_topic_obj(**overrides):
    """Create a mock Topic ORM object."""
    defaults = {
        "id": 1,
        "pikabu_id": "science",
        "name": "Наука",
        "subscribers_count": 12345,
        "url": "https://pikabu.ru/community/science",
        "last_fetched_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# _parse_communities_html — pure function, no mocks needed
# ---------------------------------------------------------------------------

class TestParseCommunities:
    def test_parses_multiple_communities(self):
        result = TopicManager._parse_communities_html(SAMPLE_COMMUNITIES_HTML)
        assert len(result) == 3

    def test_extracts_name(self):
        result = TopicManager._parse_communities_html(SAMPLE_COMMUNITIES_HTML)
        assert result[0]["name"] == "Наука"
        assert result[1]["name"] == "Игры"

    def test_extracts_pikabu_id(self):
        result = TopicManager._parse_communities_html(SAMPLE_COMMUNITIES_HTML)
        assert result[0]["pikabu_id"] == "science"
        assert result[1]["pikabu_id"] == "gaming"

    def test_extracts_url(self):
        result = TopicManager._parse_communities_html(SAMPLE_COMMUNITIES_HTML)
        assert result[0]["url"] == "https://pikabu.ru/community/science"

    def test_extracts_subscribers_with_spaces(self):
        result = TopicManager._parse_communities_html(SAMPLE_COMMUNITIES_HTML)
        assert result[0]["subscribers_count"] == 12345

    def test_extracts_subscribers_plain_number(self):
        result = TopicManager._parse_communities_html(SAMPLE_COMMUNITIES_HTML)
        assert result[1]["subscribers_count"] == 67890

    def test_missing_subscribers_returns_none(self):
        result = TopicManager._parse_communities_html(SAMPLE_COMMUNITIES_HTML)
        assert result[2]["subscribers_count"] is None

    def test_empty_html_returns_empty_list(self):
        result = TopicManager._parse_communities_html(EMPTY_HTML)
        assert result == []

    def test_absolute_url_preserved(self):
        html = """
        <div class="communities-item" data-community-id="ext">
          <a href="https://pikabu.ru/community/ext">
            <span class="communities-item__title">External</span>
          </a>
        </div>
        """
        result = TopicManager._parse_communities_html(html)
        assert result[0]["url"] == "https://pikabu.ru/community/ext"

    def test_fallback_pikabu_id_from_href(self):
        html = """
        <div class="communities-item">
          <a href="/community/fallback-id">
            <span class="communities-item__title">Fallback</span>
          </a>
        </div>
        """
        result = TopicManager._parse_communities_html(html)
        assert result[0]["pikabu_id"] == "fallback-id"


# ---------------------------------------------------------------------------
# _scrape_communities — mocked HTTP
# ---------------------------------------------------------------------------

class TestScrapeCommunities:
    @pytest.fixture
    def manager(self):
        session = AsyncMock()
        return TopicManager(session)

    @pytest.mark.asyncio
    async def test_success(self, manager):
        mock_response = httpx.Response(
            status_code=200,
            text=SAMPLE_COMMUNITIES_HTML,
            request=httpx.Request("GET", "https://pikabu.ru/communities"),
        )
        with patch("app.services.topic_manager.httpx.AsyncClient") as mock_cls:
            ctx = AsyncMock()
            ctx.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=ctx)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await manager._scrape_communities()

        assert len(result) == 3
        assert result[0]["name"] == "Наука"

    @pytest.mark.asyncio
    async def test_http_error_raises(self, manager):
        mock_response = httpx.Response(
            status_code=503,
            request=httpx.Request("GET", "https://pikabu.ru/communities"),
        )
        with patch("app.services.topic_manager.httpx.AsyncClient") as mock_cls:
            ctx = AsyncMock()
            ctx.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=ctx)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(TopicManagerError, match="HTTP 503"):
                await manager._scrape_communities()

    @pytest.mark.asyncio
    async def test_network_error_raises(self, manager):
        with patch("app.services.topic_manager.httpx.AsyncClient") as mock_cls:
            ctx = AsyncMock()
            ctx.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=ctx)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(TopicManagerError, match="сетевая ошибка"):
                await manager._scrape_communities()


# ---------------------------------------------------------------------------
# get_topic_info — mocked DB session
# ---------------------------------------------------------------------------

class TestGetTopicInfo:
    @pytest.mark.asyncio
    async def test_returns_topic_when_found(self):
        topic = _make_topic_obj(id=42)
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = topic
        session.execute = AsyncMock(return_value=mock_result)

        manager = TopicManager(session)
        result = await manager.get_topic_info(42)

        assert result is topic
        assert result.id == 42

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        manager = TopicManager(session)
        result = await manager.get_topic_info(999)

        assert result is None


# ---------------------------------------------------------------------------
# _get_cached_topics — cache freshness logic
# ---------------------------------------------------------------------------

class TestCacheLogic:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_topics(self):
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        manager = TopicManager(session)
        result = await manager._get_cached_topics()
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_topics_when_fresh(self):
        fresh_time = datetime.now(timezone.utc) - timedelta(hours=1)
        topics = [_make_topic_obj(last_fetched_at=fresh_time)]

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = topics
        session.execute = AsyncMock(return_value=mock_result)

        manager = TopicManager(session)
        result = await manager._get_cached_topics()
        assert result == topics

    @pytest.mark.asyncio
    async def test_returns_none_when_stale(self):
        stale_time = datetime.now(timezone.utc) - timedelta(hours=25)
        topics = [_make_topic_obj(last_fetched_at=stale_time)]

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = topics
        session.execute = AsyncMock(return_value=mock_result)

        manager = TopicManager(session)
        result = await manager._get_cached_topics()
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_fetch_timestamp(self):
        topics = [_make_topic_obj(last_fetched_at=None)]

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = topics
        session.execute = AsyncMock(return_value=mock_result)

        manager = TopicManager(session)
        result = await manager._get_cached_topics()
        assert result is None


# ---------------------------------------------------------------------------
# filter_topics — case-insensitive substring filtering
# ---------------------------------------------------------------------------

class TestFilterTopics:
    """Tests for both the standalone filter_topics() and TopicManager.filter_topics()."""

    def _topics(self):
        return [
            _make_topic_obj(id=1, name="Наука"),
            _make_topic_obj(id=2, name="Игры"),
            _make_topic_obj(id=3, name="Научная фантастика"),
            _make_topic_obj(id=4, name="ПРОГРАММИРОВАНИЕ"),
        ]

    # -- standalone function --

    def test_empty_search_returns_all(self):
        topics = self._topics()
        assert len(filter_topics(topics, "")) == 4

    def test_case_insensitive_match(self):
        topics = self._topics()
        result = filter_topics(topics, "наук")
        names = [t.name for t in result]
        assert "Наука" in names
        assert len(result) == 1

    def test_partial_match_across_topics(self):
        topics = self._topics()
        result = filter_topics(topics, "нау")
        names = [t.name for t in result]
        assert "Наука" in names
        assert "Научная фантастика" in names
        assert len(result) == 2

    def test_uppercase_search(self):
        topics = self._topics()
        result = filter_topics(topics, "ИГРЫ")
        assert len(result) == 1
        assert result[0].name == "Игры"

    def test_no_match_returns_empty(self):
        topics = self._topics()
        assert filter_topics(topics, "xyz") == []

    def test_empty_list_returns_empty(self):
        assert filter_topics([], "test") == []

    # -- TopicManager static method delegates correctly --

    def test_manager_filter_delegates(self):
        topics = self._topics()
        result = TopicManager.filter_topics(topics, "програм")
        assert len(result) == 1
        assert result[0].name == "ПРОГРАММИРОВАНИЕ"
