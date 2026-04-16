"""Preservation property tests for parser date sort fix.

These tests capture the CURRENT (unfixed) behavior of the parser so we can
verify no regressions after the fix is applied.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

On UNFIXED code, all tests are EXPECTED TO PASS — they confirm baseline
behavior that must be preserved.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.services.parser import ParserService


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Random post titles (simple ASCII)
post_titles = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz "),
    min_size=3,
    max_size=40,
).filter(lambda t: t.strip())

# Random post bodies
post_bodies = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789 .!"),
    min_size=0,
    max_size=100,
)

# Random ratings
ratings = st.integers(min_value=-100, max_value=10000)

# Random comment counts
comment_counts = st.integers(min_value=0, max_value=5000)


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _make_post_html(
    post_id: str,
    title: str,
    body: str,
    dt: datetime,
    rating: int = 10,
    comments_count: int = 2,
) -> str:
    """Create a minimal post HTML element."""
    dt_str = dt.isoformat()
    return (
        f'<article class="story" data-story-id="{post_id}">'
        f'<a class="story__title-link" href="/story/test_{post_id}">{title}</a>'
        f'<div class="story__content-inner">{body}</div>'
        f'<time datetime="{dt_str}">date</time>'
        f'<span class="story__rating-count">{rating}</span>'
        f'<span class="story__comments-count">{comments_count}</span>'
        f'</article>'
    )


def _wrap_html(inner: str) -> str:
    return f"<html><body>{inner}</body></html>"


EMPTY_PAGE_HTML = "<html><body><p>No stories</p></body></html>"


# ---------------------------------------------------------------------------
# Hypothesis strategy: a list of posts with random dates
# ---------------------------------------------------------------------------

@st.composite
def post_sets(draw, min_posts=1, max_posts=8):
    """Generate a list of (post_id, title, body, datetime, rating, comments) tuples."""
    n = draw(st.integers(min_value=min_posts, max_value=max_posts))
    posts = []
    for i in range(n):
        # Random offset from now: -400 to +1 days (some fresh, some old)
        offset_hours = draw(st.integers(min_value=-400 * 24, max_value=24))
        dt = datetime.now(timezone.utc) + timedelta(hours=offset_hours)
        title = draw(post_titles)
        body = draw(post_bodies)
        rating = draw(ratings)
        cc = draw(comment_counts)
        posts.append((str(1000 + i), title, body, dt, rating, cc))
    return posts


# ---------------------------------------------------------------------------
# Property-Based Tests
# ---------------------------------------------------------------------------

class TestPreservationPropertyFiltering:
    """Property 2: Preservation — post filtering by `since` is correct.

    **Validates: Requirements 3.2**

    For any set of posts with various dates, parse_posts filters by `since`
    and returns only posts with published_at >= since.
    """

    @given(posts=post_sets(min_posts=1, max_posts=8))
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_filtering_returns_only_fresh_posts(self, posts):
        """Posts with published_at >= since are kept; older ones are dropped.

        **Validates: Requirements 3.2**
        """
        # Pick a since threshold: 30 days ago
        since = datetime.now(timezone.utc) - timedelta(days=30)

        # Build page HTML from generated posts
        inner = "".join(
            _make_post_html(pid, title, body, dt, rating, cc)
            for pid, title, body, dt, rating, cc in posts
        )
        page_html = _wrap_html(inner)

        async def mock_fetch_page(url: str) -> str:
            if "page=" not in url:
                return page_html
            return EMPTY_PAGE_HTML

        session = AsyncMock()
        parser = ParserService(session)

        with patch.object(parser, "_fetch_page", side_effect=mock_fetch_page):
            result = await parser.parse_posts("https://pikabu.ru/community/test", since)

        # Compute expected: only posts with dt >= since
        expected_ids = {
            pid for pid, _, _, dt, _, _ in posts if dt >= since
        }
        result_ids = {p["pikabu_post_id"] for p in result}

        assert result_ids == expected_ids, (
            f"Expected post IDs {expected_ids}, got {result_ids}"
        )


class TestPreservationPropertyEarlyExit:
    """Property 2: Preservation — early-exit when all posts on a page are old.

    **Validates: Requirements 3.3**

    When all posts on a page are older than `since`, pagination stops.
    """

    @given(
        num_old_posts=st.integers(min_value=1, max_value=5),
        old_days_offset=st.integers(min_value=60, max_value=365),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_early_exit_on_all_old_posts(self, num_old_posts, old_days_offset):
        """When a page has only old posts, pagination stops and no posts are returned.

        **Validates: Requirements 3.3**
        """
        since = datetime.now(timezone.utc) - timedelta(days=30)
        old_dt = datetime.now(timezone.utc) - timedelta(days=old_days_offset)

        # Build a page with only old posts
        inner = "".join(
            _make_post_html(str(3000 + i), f"Old Post {i}", "old body", old_dt)
            for i in range(num_old_posts)
        )
        page_html = _wrap_html(inner)

        captured_urls: list[str] = []

        async def mock_fetch_page(url: str) -> str:
            captured_urls.append(url)
            if len(captured_urls) == 1:
                return page_html
            return EMPTY_PAGE_HTML

        session = AsyncMock()
        parser = ParserService(session)

        with patch.object(parser, "_fetch_page", side_effect=mock_fetch_page):
            result = await parser.parse_posts("https://pikabu.ru/community/test", since)

        # No fresh posts should be returned
        assert len(result) == 0

        # Early-exit: should only fetch page 1 (no page 2 request)
        assert len(captured_urls) == 1, (
            f"Expected early-exit after 1 page, but fetched {len(captured_urls)} URLs"
        )


# ---------------------------------------------------------------------------
# Example-Based Preservation Tests
# ---------------------------------------------------------------------------

class TestPreservationPaginationURL:
    """Verify pagination URL pattern is appended correctly.

    **Validates: Requirements 3.1**
    """

    @pytest.mark.asyncio
    async def test_page1_uses_raw_url(self):
        """Page 1 uses the topic URL as-is (no ?page=1).

        **Validates: Requirements 3.1**
        """
        since = datetime.now(timezone.utc) - timedelta(days=30)
        fresh_dt = datetime.now(timezone.utc) - timedelta(hours=1)

        page_html = _wrap_html(
            _make_post_html("4001", "Fresh Post", "body", fresh_dt)
        )

        captured_urls: list[str] = []

        async def mock_fetch_page(url: str) -> str:
            captured_urls.append(url)
            if len(captured_urls) == 1:
                return page_html
            return EMPTY_PAGE_HTML

        session = AsyncMock()
        parser = ParserService(session)

        with patch.object(parser, "_fetch_page", side_effect=mock_fetch_page):
            await parser.parse_posts("https://pikabu.ru/community/test", since)

        # Page 1 URL should include sort=date (added by the fix)
        assert captured_urls[0] == "https://pikabu.ru/community/test?sort=date"

    @pytest.mark.asyncio
    async def test_page2_appends_query_param(self):
        """Page 2 appends ?page=2 to the topic URL.

        **Validates: Requirements 3.1**
        """
        since = datetime.now(timezone.utc) - timedelta(days=30)
        fresh_dt = datetime.now(timezone.utc) - timedelta(hours=1)

        page1_html = _wrap_html(
            _make_post_html("5001", "Post A", "body", fresh_dt)
        )
        page2_html = _wrap_html(
            _make_post_html("5002", "Post B", "body", fresh_dt)
        )

        captured_urls: list[str] = []

        async def mock_fetch_page(url: str) -> str:
            captured_urls.append(url)
            if len(captured_urls) == 1:
                return page1_html
            elif len(captured_urls) == 2:
                return page2_html
            return EMPTY_PAGE_HTML

        session = AsyncMock()
        parser = ParserService(session)

        with patch.object(parser, "_fetch_page", side_effect=mock_fetch_page):
            await parser.parse_posts("https://pikabu.ru/community/test", since)

        assert len(captured_urls) >= 2
        assert captured_urls[1] == "https://pikabu.ru/community/test?sort=date&page=2"

    @pytest.mark.asyncio
    async def test_page3_appends_query_param(self):
        """Page 3 appends ?page=3 to the topic URL.

        **Validates: Requirements 3.1**
        """
        since = datetime.now(timezone.utc) - timedelta(days=30)
        fresh_dt = datetime.now(timezone.utc) - timedelta(hours=1)

        page1_html = _wrap_html(
            _make_post_html("6001", "Post 1", "body", fresh_dt)
        )
        page2_html = _wrap_html(
            _make_post_html("6002", "Post 2", "body", fresh_dt)
        )
        page3_html = _wrap_html(
            _make_post_html("6003", "Post 3", "body", fresh_dt)
        )

        captured_urls: list[str] = []

        async def mock_fetch_page(url: str) -> str:
            captured_urls.append(url)
            if len(captured_urls) == 1:
                return page1_html
            elif len(captured_urls) == 2:
                return page2_html
            elif len(captured_urls) == 3:
                return page3_html
            return EMPTY_PAGE_HTML

        session = AsyncMock()
        parser = ParserService(session)

        with patch.object(parser, "_fetch_page", side_effect=mock_fetch_page):
            await parser.parse_posts("https://pikabu.ru/community/test", since)

        assert len(captured_urls) >= 3
        assert captured_urls[2] == "https://pikabu.ru/community/test?sort=date&page=3"


class TestPreservationHTMLParsing:
    """Verify _extract_posts_from_html and _extract_comments_from_html output.

    **Validates: Requirements 3.5**
    """

    def test_extract_posts_returns_expected_fields(self):
        """_extract_posts_from_html returns dicts with all expected fields.

        **Validates: Requirements 3.5**
        """
        dt = datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc)
        html = _wrap_html(
            _make_post_html("7001", "Test Title", "Test Body", dt, 42, 7)
        )

        posts = ParserService._extract_posts_from_html(html)

        assert len(posts) == 1
        post = posts[0]
        assert post["pikabu_post_id"] == "7001"
        assert post["title"] == "Test Title"
        assert post["body"] == "Test Body"
        assert post["published_at"] == dt
        assert post["rating"] == 42
        assert post["comments_count"] == 7
        assert post["url"] == "https://pikabu.ru/story/test_7001"

    def test_extract_posts_field_keys(self):
        """Extracted post dicts have exactly the expected keys.

        **Validates: Requirements 3.5**
        """
        dt = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
        html = _wrap_html(
            _make_post_html("7002", "Title", "Body", dt)
        )

        posts = ParserService._extract_posts_from_html(html)
        assert len(posts) == 1

        expected_keys = {
            "pikabu_post_id", "title", "body",
            "published_at", "rating", "comments_count", "url",
        }
        assert set(posts[0].keys()) == expected_keys

    def test_extract_comments_returns_expected_fields(self):
        """_extract_comments_from_html returns dicts with all expected fields.

        **Validates: Requirements 3.5**
        """
        html = """<html><body>
        <div class="comment" data-comment-id="8001">
          <div class="comment__content">Great comment</div>
          <time datetime="2025-06-15T14:00:00+00:00">Jun 15</time>
          <span class="comment__rating-count">5</span>
        </div>
        </body></html>"""

        comments = ParserService._extract_comments_from_html(html)

        assert len(comments) == 1
        comment = comments[0]
        assert comment["pikabu_comment_id"] == "8001"
        assert comment["body"] == "Great comment"
        assert comment["published_at"] == datetime(2025, 6, 15, 14, 0, tzinfo=timezone.utc)
        assert comment["rating"] == 5

    def test_extract_comments_field_keys(self):
        """Extracted comment dicts have exactly the expected keys.

        **Validates: Requirements 3.5**
        """
        html = """<html><body>
        <div class="comment" data-comment-id="8002">
          <div class="comment__content">Some text</div>
          <time datetime="2025-01-01T00:00:00+00:00">Jan 1</time>
          <span class="comment__rating-count">0</span>
        </div>
        </body></html>"""

        comments = ParserService._extract_comments_from_html(html)
        assert len(comments) == 1

        expected_keys = {"pikabu_comment_id", "body", "published_at", "rating"}
        assert set(comments[0].keys()) == expected_keys


class TestPreservationMixedFreshOld:
    """Verify filtering with mixed fresh/old posts on a single page.

    **Validates: Requirements 3.2, 3.3**
    """

    @pytest.mark.asyncio
    async def test_mixed_page_keeps_fresh_drops_old(self):
        """A page with both fresh and old posts: only fresh ones are returned.

        **Validates: Requirements 3.2**
        """
        since = datetime.now(timezone.utc) - timedelta(days=30)
        fresh_dt = datetime.now(timezone.utc) - timedelta(hours=5)
        old_dt = datetime.now(timezone.utc) - timedelta(days=60)

        inner = (
            _make_post_html("9001", "Fresh Post", "fresh body", fresh_dt)
            + _make_post_html("9002", "Old Post", "old body", old_dt)
        )
        page_html = _wrap_html(inner)

        async def mock_fetch_page(url: str) -> str:
            if "page=" not in url:
                return page_html
            return EMPTY_PAGE_HTML

        session = AsyncMock()
        parser = ParserService(session)

        with patch.object(parser, "_fetch_page", side_effect=mock_fetch_page):
            result = await parser.parse_posts("https://pikabu.ru/community/test", since)

        assert len(result) == 1
        assert result[0]["pikabu_post_id"] == "9001"
        assert result[0]["title"] == "Fresh Post"

    @pytest.mark.asyncio
    async def test_mixed_page_does_not_early_exit(self):
        """A page with at least one fresh post does NOT trigger early-exit.

        **Validates: Requirements 3.3**
        """
        since = datetime.now(timezone.utc) - timedelta(days=30)
        fresh_dt = datetime.now(timezone.utc) - timedelta(hours=5)
        old_dt = datetime.now(timezone.utc) - timedelta(days=60)

        # Page 1: mixed fresh + old
        page1_inner = (
            _make_post_html("9101", "Fresh", "body", fresh_dt)
            + _make_post_html("9102", "Old", "body", old_dt)
        )
        page1_html = _wrap_html(page1_inner)

        captured_urls: list[str] = []

        async def mock_fetch_page(url: str) -> str:
            captured_urls.append(url)
            if len(captured_urls) == 1:
                return page1_html
            return EMPTY_PAGE_HTML

        session = AsyncMock()
        parser = ParserService(session)

        with patch.object(parser, "_fetch_page", side_effect=mock_fetch_page):
            await parser.parse_posts("https://pikabu.ru/community/test", since)

        # Should have fetched page 2 (no early-exit on mixed page)
        assert len(captured_urls) == 2, (
            f"Expected 2 fetches (page 1 + page 2), got {len(captured_urls)}"
        )
