"""Tests for ParserService — mocked HTTP, real HTML parsing logic."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.parser import ParserService, ParserError, _parse_datetime, _parse_int


# ---------------------------------------------------------------------------
# Sample HTML fixtures
# ---------------------------------------------------------------------------

def _make_post_html(
    story_id: str = "12345",
    title: str = "Test Post Title",
    body: str = "Post body text here",
    dt: str = "2025-01-15T12:00:00+00:00",
    rating: str = "42",
    comments_count: str = "10",
    url: str = "/story/test_post_12345",
) -> str:
    return f"""
    <article class="story" data-story-id="{story_id}">
      <a class="story__title-link" href="{url}">{title}</a>
      <div class="story__content-inner">{body}</div>
      <time datetime="{dt}">15 Jan</time>
      <span class="story__rating-count">{rating}</span>
      <span class="story__comments-count">{comments_count}</span>
    </article>
    """


def _make_comment_html(
    comment_id: str = "99001",
    body: str = "This is a comment",
    dt: str = "2025-01-15T14:00:00+00:00",
    rating: str = "5",
) -> str:
    return f"""
    <div class="comment" data-comment-id="{comment_id}">
      <div class="comment__content">{body}</div>
      <time datetime="{dt}">15 Jan</time>
      <span class="comment__rating-count">{rating}</span>
    </div>
    """


SAMPLE_TOPIC_PAGE_HTML = f"""
<html><body>
{_make_post_html("111", "First Post", "Body one", "2025-01-10T10:00:00+00:00", "100", "20", "/story/first_111")}
{_make_post_html("222", "Second Post", "Body two", "2025-01-12T15:30:00+00:00", "-5", "3", "/story/second_222")}
</body></html>
"""

SAMPLE_POST_PAGE_HTML = f"""
<html><body>
{_make_comment_html("501", "Great post!", "2025-01-10T11:00:00+00:00", "12")}
{_make_comment_html("502", "I disagree", "2025-01-10T12:00:00+00:00", "-3")}
</body></html>
"""

EMPTY_PAGE_HTML = "<html><body><p>No stories here</p></body></html>"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_topic_obj(topic_id: int = 1, url: str = "https://pikabu.ru/community/test"):
    obj = MagicMock()
    obj.id = topic_id
    obj.url = url
    obj.name = "Test Topic"
    return obj


def _mock_session():
    return AsyncMock()


# ---------------------------------------------------------------------------
# _extract_posts_from_html — pure parsing, no HTTP
# ---------------------------------------------------------------------------

class TestExtractPostsFromHtml:
    def test_extracts_multiple_posts(self):
        posts = ParserService._extract_posts_from_html(SAMPLE_TOPIC_PAGE_HTML)
        assert len(posts) == 2

    def test_extracts_title(self):
        posts = ParserService._extract_posts_from_html(SAMPLE_TOPIC_PAGE_HTML)
        assert posts[0]["title"] == "First Post"
        assert posts[1]["title"] == "Second Post"

    def test_extracts_body(self):
        posts = ParserService._extract_posts_from_html(SAMPLE_TOPIC_PAGE_HTML)
        assert posts[0]["body"] == "Body one"

    def test_extracts_pikabu_post_id(self):
        posts = ParserService._extract_posts_from_html(SAMPLE_TOPIC_PAGE_HTML)
        assert posts[0]["pikabu_post_id"] == "111"
        assert posts[1]["pikabu_post_id"] == "222"

    def test_extracts_url(self):
        posts = ParserService._extract_posts_from_html(SAMPLE_TOPIC_PAGE_HTML)
        assert posts[0]["url"] == "https://pikabu.ru/story/first_111"

    def test_extracts_published_at(self):
        posts = ParserService._extract_posts_from_html(SAMPLE_TOPIC_PAGE_HTML)
        assert posts[0]["published_at"] == datetime(2025, 1, 10, 10, 0, tzinfo=timezone.utc)

    def test_extracts_rating(self):
        posts = ParserService._extract_posts_from_html(SAMPLE_TOPIC_PAGE_HTML)
        assert posts[0]["rating"] == 100
        assert posts[1]["rating"] == -5

    def test_extracts_comments_count(self):
        posts = ParserService._extract_posts_from_html(SAMPLE_TOPIC_PAGE_HTML)
        assert posts[0]["comments_count"] == 20
        assert posts[1]["comments_count"] == 3

    def test_empty_html_returns_empty(self):
        posts = ParserService._extract_posts_from_html(EMPTY_PAGE_HTML)
        assert posts == []

    def test_missing_title_skips_post(self):
        html = """
        <article class="story" data-story-id="999">
          <div class="story__content-inner">Body without title</div>
        </article>
        """
        posts = ParserService._extract_posts_from_html(html)
        assert posts == []

    def test_missing_body_returns_empty_string(self):
        html = _make_post_html(body="")
        # Remove the body div entirely
        html = html.replace('<div class="story__content-inner"></div>', "")
        posts = ParserService._extract_posts_from_html(html)
        assert len(posts) == 1
        assert posts[0]["body"] == ""

    def test_missing_rating_defaults_to_zero(self):
        html = """
        <article class="story" data-story-id="777">
          <a class="story__title-link" href="/story/test_777">Title</a>
          <time datetime="2025-01-15T12:00:00+00:00">15 Jan</time>
        </article>
        """
        posts = ParserService._extract_posts_from_html(html)
        assert len(posts) == 1
        assert posts[0]["rating"] == 0
        assert posts[0]["comments_count"] == 0


# ---------------------------------------------------------------------------
# _extract_comments_from_html — pure parsing, no HTTP
# ---------------------------------------------------------------------------

class TestExtractCommentsFromHtml:
    def test_extracts_multiple_comments(self):
        comments = ParserService._extract_comments_from_html(SAMPLE_POST_PAGE_HTML)
        assert len(comments) == 2

    def test_extracts_body(self):
        comments = ParserService._extract_comments_from_html(SAMPLE_POST_PAGE_HTML)
        assert comments[0]["body"] == "Great post!"
        assert comments[1]["body"] == "I disagree"

    def test_extracts_comment_id(self):
        comments = ParserService._extract_comments_from_html(SAMPLE_POST_PAGE_HTML)
        assert comments[0]["pikabu_comment_id"] == "501"

    def test_extracts_published_at(self):
        comments = ParserService._extract_comments_from_html(SAMPLE_POST_PAGE_HTML)
        assert comments[0]["published_at"] == datetime(2025, 1, 10, 11, 0, tzinfo=timezone.utc)

    def test_extracts_rating(self):
        comments = ParserService._extract_comments_from_html(SAMPLE_POST_PAGE_HTML)
        assert comments[0]["rating"] == 12
        assert comments[1]["rating"] == -3

    def test_empty_html_returns_empty(self):
        comments = ParserService._extract_comments_from_html(EMPTY_PAGE_HTML)
        assert comments == []

    def test_missing_body_skips_comment(self):
        html = """
        <div class="comment" data-comment-id="888">
          <time datetime="2025-01-15T12:00:00+00:00">15 Jan</time>
        </div>
        """
        comments = ParserService._extract_comments_from_html(html)
        assert comments == []

    def test_empty_body_skips_comment(self):
        html = """
        <div class="comment" data-comment-id="888">
          <div class="comment__content">   </div>
          <time datetime="2025-01-15T12:00:00+00:00">15 Jan</time>
        </div>
        """
        comments = ParserService._extract_comments_from_html(html)
        assert comments == []

    def test_missing_comment_id_skips(self):
        html = """
        <div class="comment">
          <div class="comment__content">Some text</div>
        </div>
        """
        comments = ParserService._extract_comments_from_html(html)
        assert comments == []

    def test_fallback_comment_id_from_element_id(self):
        html = """
        <div class="comment" id="comment_12345">
          <div class="comment__content">Fallback ID comment</div>
          <time datetime="2025-01-15T12:00:00+00:00">15 Jan</time>
        </div>
        """
        comments = ParserService._extract_comments_from_html(html)
        assert len(comments) == 1
        assert comments[0]["pikabu_comment_id"] == "12345"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestParseDatetime:
    def test_valid_iso_datetime(self):
        from bs4 import BeautifulSoup
        html = '<time datetime="2025-06-15T10:30:00+00:00">Jun 15</time>'
        el = BeautifulSoup(html, "html.parser").find("time")
        result = _parse_datetime(el)
        assert result == datetime(2025, 6, 15, 10, 30, tzinfo=timezone.utc)

    def test_none_element_returns_now(self):
        result = _parse_datetime(None)
        assert (datetime.now(timezone.utc) - result).total_seconds() < 2

    def test_invalid_datetime_returns_now(self):
        from bs4 import BeautifulSoup
        html = '<time datetime="not-a-date">Bad</time>'
        el = BeautifulSoup(html, "html.parser").find("time")
        result = _parse_datetime(el)
        assert (datetime.now(timezone.utc) - result).total_seconds() < 2


class TestParseInt:
    def test_simple_number(self):
        from bs4 import BeautifulSoup
        html = '<span>42</span>'
        el = BeautifulSoup(html, "html.parser").find("span")
        assert _parse_int(el) == 42

    def test_negative_number(self):
        from bs4 import BeautifulSoup
        html = '<span>-15</span>'
        el = BeautifulSoup(html, "html.parser").find("span")
        assert _parse_int(el) == -15

    def test_number_with_text(self):
        from bs4 import BeautifulSoup
        html = '<span>123 комментария</span>'
        el = BeautifulSoup(html, "html.parser").find("span")
        assert _parse_int(el) == 123

    def test_none_returns_zero(self):
        assert _parse_int(None) == 0

    def test_empty_text_returns_zero(self):
        from bs4 import BeautifulSoup
        html = '<span></span>'
        el = BeautifulSoup(html, "html.parser").find("span")
        assert _parse_int(el) == 0

    def test_from_attribute(self):
        from bs4 import BeautifulSoup
        html = '<span data-rating="77">text</span>'
        el = BeautifulSoup(html, "html.parser").find("span")
        assert _parse_int(el, attr="data-rating") == 77


# ---------------------------------------------------------------------------
# _fetch_page — mocked HTTP
# ---------------------------------------------------------------------------

class TestFetchPage:
    @pytest.fixture
    def parser(self):
        return ParserService(_mock_session())

    @staticmethod
    def _make_curl_response(status_code: int, text: str = ""):
        """Create a mock curl_cffi response."""
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        return resp

    @pytest.mark.asyncio
    async def test_success(self, parser):
        resp = self._make_curl_response(200, "<html>OK</html>")
        with patch("app.services.parser.curl_requests.get", return_value=resp):
            result = await parser._fetch_page("https://pikabu.ru/test")
        assert result == "<html>OK</html>"

    @pytest.mark.asyncio
    async def test_http_4xx_error_raises_immediately(self, parser):
        """Non-retryable client errors (e.g. 404) raise immediately."""
        resp = self._make_curl_response(404)
        with patch("app.services.parser.curl_requests.get", return_value=resp):
            with pytest.raises(ParserError, match="HTTP 404"):
                await parser._fetch_page("https://pikabu.ru/test")

    @pytest.mark.asyncio
    async def test_network_error_raises(self, parser):
        with patch("app.services.parser.curl_requests.get", side_effect=Exception("connection refused")):
            with pytest.raises(ParserError, match="Сетевая ошибка"):
                await parser._fetch_page("https://pikabu.ru/test")


# ---------------------------------------------------------------------------
# _fetch_page — retry logic (task 4.2)
# ---------------------------------------------------------------------------

class TestFetchPageRetry:
    """Tests for retry behaviour in _fetch_page.

    asyncio.sleep is patched so tests run instantly.
    """

    @pytest.fixture
    def parser(self):
        return ParserService(_mock_session())

    @staticmethod
    def _make_curl_response(status_code: int, text: str = ""):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = text
        return resp

    # -- HTTP 429 retry -------------------------------------------------------

    @pytest.mark.asyncio
    async def test_429_retries_then_succeeds(self, parser):
        """HTTP 429 → pause 60 s → retry → success."""
        responses = [
            self._make_curl_response(429),
            self._make_curl_response(200, "<html>OK</html>"),
        ]
        with patch("app.services.parser.curl_requests.get", side_effect=responses):
            with patch("app.services.parser.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await parser._fetch_page("https://pikabu.ru/test")

        assert result == "<html>OK</html>"
        mock_sleep.assert_awaited_once_with(60)

    @pytest.mark.asyncio
    async def test_429_multiple_retries(self, parser):
        """Multiple consecutive 429s are all retried."""
        responses = [
            self._make_curl_response(429),
            self._make_curl_response(429),
            self._make_curl_response(200, "<html>OK</html>"),
        ]
        with patch("app.services.parser.curl_requests.get", side_effect=responses):
            with patch("app.services.parser.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await parser._fetch_page("https://pikabu.ru/test")

        assert result == "<html>OK</html>"
        assert mock_sleep.await_count == 2
        mock_sleep.assert_awaited_with(60)

    # -- HTTP 5xx retry -------------------------------------------------------

    @pytest.mark.asyncio
    async def test_5xx_retries_then_succeeds(self, parser):
        """HTTP 500 → retry with 10 s delay → success on 2nd attempt."""
        responses = [
            self._make_curl_response(500),
            self._make_curl_response(200, "<html>OK</html>"),
        ]
        with patch("app.services.parser.curl_requests.get", side_effect=responses):
            with patch("app.services.parser.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await parser._fetch_page("https://pikabu.ru/test")

        assert result == "<html>OK</html>"
        mock_sleep.assert_awaited_once_with(10)

    @pytest.mark.asyncio
    async def test_5xx_exhausts_retries(self, parser):
        """HTTP 503 × 4 (1 initial + 3 retries) → ParserError."""
        responses = [self._make_curl_response(503)] * 4
        with patch("app.services.parser.curl_requests.get", side_effect=responses):
            with patch("app.services.parser.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                with pytest.raises(ParserError, match="HTTP 503"):
                    await parser._fetch_page("https://pikabu.ru/test")

        # 3 retries → 3 sleep calls
        assert mock_sleep.await_count == 3
        mock_sleep.assert_awaited_with(10)

    @pytest.mark.asyncio
    async def test_5xx_succeeds_on_last_retry(self, parser):
        """HTTP 502 × 3 then success on the 4th attempt (3rd retry)."""
        responses = [
            self._make_curl_response(502),
            self._make_curl_response(502),
            self._make_curl_response(502),
            self._make_curl_response(200, "<html>OK</html>"),
        ]
        with patch("app.services.parser.curl_requests.get", side_effect=responses):
            with patch("app.services.parser.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await parser._fetch_page("https://pikabu.ru/test")

        assert result == "<html>OK</html>"
        assert mock_sleep.await_count == 3

    # -- Network errors -------------------------------------------------------

    @pytest.mark.asyncio
    async def test_network_error_raises_parser_error(self, parser):
        """Network errors raise ParserError immediately (no retry)."""
        with patch("app.services.parser.curl_requests.get", side_effect=Exception("connection refused")):
            with pytest.raises(ParserError, match="Сетевая ошибка"):
                await parser._fetch_page("https://pikabu.ru/test")

    @pytest.mark.asyncio
    async def test_timeout_error_raises_parser_error(self, parser):
        """Timeout errors raise ParserError."""
        with patch("app.services.parser.curl_requests.get", side_effect=Exception("read timed out")):
            with pytest.raises(ParserError, match="Сетевая ошибка"):
                await parser._fetch_page("https://pikabu.ru/test")

    # -- Mixed scenarios -------------------------------------------------------

    @pytest.mark.asyncio
    async def test_429_then_5xx_then_success(self, parser):
        """429 → retry → 500 → retry → success."""
        responses = [
            self._make_curl_response(429),
            self._make_curl_response(500),
            self._make_curl_response(200, "<html>OK</html>"),
        ]
        with patch("app.services.parser.curl_requests.get", side_effect=responses):
            with patch("app.services.parser.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await parser._fetch_page("https://pikabu.ru/test")

        assert result == "<html>OK</html>"
        assert mock_sleep.await_count == 2
        # First sleep: 60 (429), second sleep: 10 (5xx)
        mock_sleep.assert_any_await(60)
        mock_sleep.assert_any_await(10)


# ---------------------------------------------------------------------------
# parse_posts — mocked _fetch_page, real HTML parsing
# ---------------------------------------------------------------------------

class TestParsePosts:
    @pytest.fixture
    def parser(self):
        return ParserService(_mock_session())

    @pytest.mark.asyncio
    async def test_returns_posts_within_date_range(self, parser):
        since = datetime(2025, 1, 1, tzinfo=timezone.utc)
        with patch.object(parser, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [SAMPLE_TOPIC_PAGE_HTML, EMPTY_PAGE_HTML]
            posts = await parser.parse_posts("https://pikabu.ru/community/test", since)

        assert len(posts) == 2
        assert posts[0]["title"] == "First Post"
        assert posts[1]["title"] == "Second Post"

    @pytest.mark.asyncio
    async def test_filters_old_posts(self, parser):
        since = datetime(2025, 1, 11, tzinfo=timezone.utc)
        with patch.object(parser, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [SAMPLE_TOPIC_PAGE_HTML, EMPTY_PAGE_HTML]
            posts = await parser.parse_posts("https://pikabu.ru/community/test", since)

        # Only "Second Post" (Jan 12) should pass; "First Post" (Jan 10) is too old
        assert len(posts) == 1
        assert posts[0]["title"] == "Second Post"

    @pytest.mark.asyncio
    async def test_stops_on_empty_page(self, parser):
        since = datetime(2025, 1, 1, tzinfo=timezone.utc)
        with patch.object(parser, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = EMPTY_PAGE_HTML
            posts = await parser.parse_posts("https://pikabu.ru/community/test", since)

        assert posts == []

    @pytest.mark.asyncio
    async def test_pagination(self, parser):
        page1 = f"""<html><body>
        {_make_post_html("p1", "Page1 Post", "Body", "2025-01-15T10:00:00+00:00", "10", "1", "/story/p1")}
        </body></html>"""
        page2 = f"""<html><body>
        {_make_post_html("p2", "Page2 Post", "Body", "2025-01-14T10:00:00+00:00", "5", "0", "/story/p2")}
        </body></html>"""

        since = datetime(2025, 1, 1, tzinfo=timezone.utc)
        with patch.object(parser, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [page1, page2, EMPTY_PAGE_HTML]
            posts = await parser.parse_posts("https://pikabu.ru/community/test", since)

        assert len(posts) == 2
        # Verify pagination URLs (sort=date is always added by the fix)
        calls = mock_fetch.call_args_list
        assert calls[0].args[0] == "https://pikabu.ru/community/test?sort=date"
        assert calls[1].args[0] == "https://pikabu.ru/community/test?sort=date&page=2"


# ---------------------------------------------------------------------------
# parse_comments — mocked _fetch_page, real HTML parsing
# ---------------------------------------------------------------------------

class TestParseComments:
    @pytest.fixture
    def parser(self):
        return ParserService(_mock_session())

    @pytest.mark.asyncio
    async def test_returns_comments(self, parser):
        with patch.object(parser, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = SAMPLE_POST_PAGE_HTML
            comments = await parser.parse_comments("https://pikabu.ru/story/test_123")

        assert len(comments) == 2
        assert comments[0]["body"] == "Great post!"
        assert comments[1]["body"] == "I disagree"

    @pytest.mark.asyncio
    async def test_empty_page_returns_empty(self, parser):
        with patch.object(parser, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = EMPTY_PAGE_HTML
            comments = await parser.parse_comments("https://pikabu.ru/story/test_123")

        assert comments == []


# ---------------------------------------------------------------------------
# parse_topic — full integration with mocked HTTP and DB
# ---------------------------------------------------------------------------

class TestParseTopic:
    def _setup_session_for_parse_topic(self, topic_obj):
        """Create a mock session that handles the DB operations in parse_topic."""
        session = AsyncMock()

        # Track added objects
        added_objects = []
        session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        # Counter for generating IDs
        call_count = {"topic": 0, "post": 0, "comment": 0, "meta": 0}

        async def mock_execute(stmt):
            mock_result = MagicMock()
            # Determine what's being queried by inspecting the statement
            stmt_str = str(stmt)

            if "topics" in stmt_str.lower() and "topic_id" not in stmt_str.lower():
                mock_result.scalar_one_or_none.return_value = topic_obj
            elif "parse_metadata" in stmt_str.lower():
                mock_result.scalar_one_or_none.return_value = None
            else:
                # For posts and comments lookups (upsert check) — return None (new)
                mock_result.scalar_one_or_none.return_value = None

            return mock_result

        session.execute = AsyncMock(side_effect=mock_execute)
        session.flush = AsyncMock()

        return session, added_objects

    @pytest.mark.asyncio
    async def test_parse_topic_success(self):
        topic = _make_topic_obj(topic_id=1, url="https://pikabu.ru/community/test")

        session, added_objects = self._setup_session_for_parse_topic(topic)
        parser = ParserService(session)

        # Use a recent date so the post passes the 30-day filter
        recent_dt = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

        post_html = f"""<html><body>
        {_make_post_html("p1", "Post 1", "Body 1", recent_dt, "10", "2", "/story/p1")}
        </body></html>"""

        comment_html = f"""<html><body>
        {_make_comment_html("c1", "Comment 1", recent_dt, "3")}
        </body></html>"""

        with patch.object(parser, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [post_html, EMPTY_PAGE_HTML, comment_html]
            result = await parser.parse_topic(1)

        assert result["posts_count"] == 1
        assert result["comments_count"] == 1

    @pytest.mark.asyncio
    async def test_parse_topic_not_found(self):
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        parser = ParserService(session)

        with pytest.raises(ParserError, match="не найдена"):
            await parser.parse_topic(999)

    @pytest.mark.asyncio
    async def test_parse_topic_with_callback(self):
        topic = _make_topic_obj(topic_id=1, url="https://pikabu.ru/community/test")
        session, _ = self._setup_session_for_parse_topic(topic)
        parser = ParserService(session)

        callback = AsyncMock()

        recent_dt = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

        post_html = f"""<html><body>
        {_make_post_html("p1", "Post 1", "Body", recent_dt, "5", "0", "/story/p1")}
        </body></html>"""

        with patch.object(parser, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [post_html, EMPTY_PAGE_HTML, EMPTY_PAGE_HTML]
            await parser.parse_topic(1, callback=callback)

        # Callback should be called: once at start (0%), once after processing the post
        assert callback.call_count >= 2
        # First call: start
        callback.assert_any_call("parsing", 0)

    @pytest.mark.asyncio
    async def test_parse_topic_no_posts(self):
        topic = _make_topic_obj(topic_id=1, url="https://pikabu.ru/community/test")
        session, _ = self._setup_session_for_parse_topic(topic)
        parser = ParserService(session)

        with patch.object(parser, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = EMPTY_PAGE_HTML
            result = await parser.parse_topic(1)

        assert result["posts_count"] == 0
        assert result["comments_count"] == 0
