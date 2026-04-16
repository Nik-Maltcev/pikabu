"""Bug condition exploration test for parser date sort fix.

This test verifies Property 1 (Bug Condition): every URL passed to _fetch_page
by parse_posts must contain the query parameter sort=date.

**Validates: Requirements 1.1, 2.1, 2.2**

On UNFIXED code, this test is EXPECTED TO FAIL — failure confirms the bug exists
because sort=date is never included in the constructed URLs.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from urllib.parse import urlparse, parse_qs

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.services.parser import ParserService


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Generate random Pikabu community path segments (lowercase letters, 3-20 chars)
community_names = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
    min_size=3,
    max_size=20,
)

# Generate since datetimes within a reasonable range (last 1-365 days)
since_datetimes = st.integers(min_value=1, max_value=365).map(
    lambda days: datetime.now(timezone.utc) - timedelta(days=days)
)


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _make_fresh_post_html(post_id: str, dt: datetime) -> str:
    """Create a minimal post HTML element with a given datetime."""
    dt_str = dt.isoformat()
    return f"""
    <article class="story" data-story-id="{post_id}">
      <a class="story__title-link" href="/story/test_{post_id}">Post {post_id}</a>
      <div class="story__content-inner">Body of post {post_id}</div>
      <time datetime="{dt_str}">date</time>
      <span class="story__rating-count">10</span>
      <span class="story__comments-count">2</span>
    </article>
    """


EMPTY_PAGE_HTML = "<html><body><p>No stories</p></body></html>"


# ---------------------------------------------------------------------------
# Bug Condition Exploration Property Test
# ---------------------------------------------------------------------------

class TestBugConditionExploration:
    """Property 1: Bug Condition — URL Missing sort=date Parameter.

    **Validates: Requirements 1.1, 2.1, 2.2**

    For any Pikabu community URL and since datetime, ALL URLs passed to
    _fetch_page by parse_posts must contain the query parameter sort=date.
    """

    @given(community=community_names, since=since_datetimes)
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_all_fetched_urls_contain_sort_date(self, community: str, since: datetime):
        """Every URL passed to _fetch_page must contain sort=date.

        **Validates: Requirements 1.1, 2.1, 2.2**

        On unfixed code this FAILS because parse_posts never adds sort=date.
        """
        assume(len(community) >= 3)

        topic_url = f"https://pikabu.ru/community/{community}"
        captured_urls: list[str] = []

        # Create a fresh post so pagination proceeds to page 2, then stops
        fresh_dt = datetime.now(timezone.utc) - timedelta(hours=1)
        page1_html = f"<html><body>{_make_fresh_post_html('1001', fresh_dt)}</body></html>"

        async def mock_fetch_page(url: str) -> str:
            captured_urls.append(url)
            if len(captured_urls) == 1:
                return page1_html  # page 1 with a fresh post
            return EMPTY_PAGE_HTML  # page 2 empty → stops

        session = AsyncMock()
        parser = ParserService(session)

        with patch.object(parser, "_fetch_page", side_effect=mock_fetch_page):
            await parser.parse_posts(topic_url, since)

        # Must have fetched at least one URL
        assert len(captured_urls) >= 1, "parse_posts should fetch at least one page"

        # ALL URLs must contain sort=date query parameter
        for url in captured_urls:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            assert "sort" in params and "date" in params["sort"], (
                f"URL missing sort=date: {url}"
            )

    @given(community=community_names, since=since_datetimes)
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_page1_has_sort_date_and_page2_has_sort_date_and_page_param(
        self, community: str, since: datetime
    ):
        """Page 1 URL must have sort=date; page 2+ must have sort=date AND page=N.

        **Validates: Requirements 1.1, 2.1, 2.2**

        On unfixed code this FAILS because neither sort=date nor proper
        query param combination is present.
        """
        assume(len(community) >= 3)

        topic_url = f"https://pikabu.ru/community/{community}"
        captured_urls: list[str] = []

        # Two pages of fresh posts, then empty → triggers pagination
        fresh_dt = datetime.now(timezone.utc) - timedelta(hours=1)
        page1_html = f"<html><body>{_make_fresh_post_html('2001', fresh_dt)}</body></html>"
        page2_html = f"<html><body>{_make_fresh_post_html('2002', fresh_dt)}</body></html>"

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
            await parser.parse_posts(topic_url, since)

        # Must have fetched at least 2 pages (page1 + page2 + empty)
        assert len(captured_urls) >= 2, (
            f"Expected at least 2 fetched URLs for pagination, got {len(captured_urls)}"
        )

        # Page 1: must contain sort=date
        parsed_p1 = urlparse(captured_urls[0])
        params_p1 = parse_qs(parsed_p1.query)
        assert "sort" in params_p1 and "date" in params_p1["sort"], (
            f"Page 1 URL missing sort=date: {captured_urls[0]}"
        )

        # Page 2+: must contain both sort=date AND page=N
        for i, url in enumerate(captured_urls[1:], start=2):
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            assert "sort" in params and "date" in params["sort"], (
                f"Page {i} URL missing sort=date: {url}"
            )
            assert "page" in params, (
                f"Page {i} URL missing page parameter: {url}"
            )
