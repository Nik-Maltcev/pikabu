"""HabrParserService — parses articles and comments from habr.com flows."""

import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Callable, Awaitable

from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup, Tag
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Post, Comment, ParseMetadata, Topic
from app.services.playwright_renderer import PlaywrightRenderer

logger = logging.getLogger(__name__)

# Type alias for progress callbacks
ProgressCallback = Callable[[str, int], Awaitable[None]] | None

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

BROWSER_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# Retry settings for Habr (no proxy needed)
RETRY_DELAY_429 = 60
RETRY_COUNT_5XX = 3
RETRY_DELAY_5XX = 10
RETRY_COUNT_NETWORK = 3
RETRY_DELAY_NETWORK = 15


class HabrParserError(Exception):
    """Base error for HabrParserService operations."""


class HabrParserService:
    """Parses articles and comments from habr.com flows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def parse_topic(
        self,
        topic_id: int,
        callback: ProgressCallback = None,
        days: int = 30,
    ) -> dict:
        """Parse all articles for a Habr flow topic from the last N days.

        Returns a dict with keys: posts_count, comments_count.
        """
        topic = await self._get_topic(topic_id)
        if topic is None:
            raise HabrParserError(f"Тема с id={topic_id} не найдена")

        if callback:
            await callback("parsing", 0)

        since = datetime.now(timezone.utc) - timedelta(days=days)
        posts_data = await self.parse_posts(topic.url, since)

        total_posts = len(posts_data)
        total_comments = 0

        async with PlaywrightRenderer() as renderer:
            for i, post_data in enumerate(posts_data):
                # Save post to DB with source="habr"
                db_post = await self._save_post(topic_id, post_data)

                # Parse and save comments for this article (skip on error)
                try:
                    comments_data = await self.parse_comments(post_data["url"], renderer=renderer)
                    for comment_data in comments_data:
                        await self._save_comment(db_post.id, comment_data)
                    total_comments += len(comments_data)
                except Exception as exc:
                    logger.warning(
                        "Skipping comments for article %s: %s",
                        post_data.get("pikabu_post_id", "?"),
                        exc,
                    )

                if callback:
                    progress = (
                        int(((i + 1) / total_posts) * 100) if total_posts > 0 else 100
                    )
                    await callback("parsing", progress)

                # Delay between posts to avoid rate limiting (same as Pikabu parser)
                await asyncio.sleep(3)

        # Update parse metadata
        await self._update_parse_metadata(topic_id, total_posts, total_comments)
        await self._session.flush()

        return {"posts_count": total_posts, "comments_count": total_comments}

    async def parse_posts(self, flow_url: str, since: datetime) -> list[dict]:
        """Fetch and parse articles from a Habr flow page with pagination.

        Pagination URL pattern:
        - Page 1: flow_url as-is (e.g. https://habr.com/ru/flows/management/articles/)
        - Page N (N>=2): {flow_url}page{N}/

        Returns a list of dicts with keys:
        title, body, published_at, rating, comments_count, url, pikabu_post_id
        """
        all_posts: list[dict] = []
        page = 1

        while True:
            if page == 1:
                page_url = flow_url
            else:
                # Ensure flow_url ends with /
                base = flow_url.rstrip("/") + "/"
                page_url = f"{base}page{page}/"

            try:
                html = await self._fetch_page(page_url)
            except HabrParserError as exc:
                # Habr returns 400 when page exceeds max pagination — treat as end
                if "HTTP 400" in str(exc):
                    logger.info("Habr pagination limit reached at page %d. Total: %d", page, len(all_posts))
                    break
                raise
            logger.info("Habr page %d: %d chars HTML", page, len(html))
            posts = self._extract_posts_from_html(html)
            logger.info("Habr page %d: %d posts extracted", page, len(posts))

            if not posts:
                break

            found_old = False
            fresh_on_page = 0
            for post in posts:
                if post["published_at"] >= since:
                    all_posts.append(post)
                    fresh_on_page += 1
                else:
                    found_old = True
                    logger.info(
                        "Old article skipped: %s date=%s",
                        post["pikabu_post_id"],
                        post["published_at"],
                    )

            # Early-exit: stop when ALL posts on page are older than since
            if found_old and fresh_on_page == 0:
                logger.info(
                    "Stopping pagination: all articles on page %d are old. Total: %d",
                    page,
                    len(all_posts),
                )
                break

            logger.info(
                "Habr page %d done: %d fresh, %d old. Total so far: %d",
                page,
                fresh_on_page,
                len(posts) - fresh_on_page,
                len(all_posts),
            )

            page += 1

        return all_posts

    async def parse_comments(self, article_url: str, renderer: PlaywrightRenderer | None = None) -> list[dict]:
        """Fetch and parse comments from a Habr article page.

        If renderer is provided, uses PlaywrightRenderer for JS-rendered comments.
        Otherwise falls back to _fetch_page (backward compatibility).

        Returns a list of dicts with keys:
        body, published_at, rating, pikabu_comment_id
        """
        if renderer:
            html = await renderer.render_page(
                article_url,
                wait_selector=".tm-comment-thread__comment, .tm-comments-wrapper",
                timeout=15000,
            )
        else:
            html = await self._fetch_page(article_url)
        return self._extract_comments_from_html(html)

    # ------------------------------------------------------------------
    # HTML parsing (static, testable without HTTP)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_posts_from_html(html: str) -> list[dict]:
        """Extract article data from a Habr flow page HTML.

        CSS selectors:
        - Article card: article.tm-articles-list__item
        - Title: a.tm-title__link (text = title, href = URL)
        - Body: .tm-article-body or .article-formatted-body
        - Date: time[datetime] or span.tm-article-datetime-published time
        - Rating: .tm-votes-meter__value
        - Comments count: .tm-article-comments-counter-link__value
        - Article ID: extracted from URL (/articles/{id}/)
        """
        soup = BeautifulSoup(html, "html.parser")
        posts: list[dict] = []
        seen_ids: set[str] = set()

        articles = soup.select("article.tm-articles-list__item")

        for article in articles:
            try:
                post = HabrParserService._parse_single_post(article)
                if post is not None and post["pikabu_post_id"] not in seen_ids:
                    seen_ids.add(post["pikabu_post_id"])
                    posts.append(post)
            except Exception:
                logger.warning(
                    "Failed to parse Habr article element, skipping",
                    exc_info=True,
                )
                continue

        return posts

    @staticmethod
    def _parse_single_post(item: Tag) -> dict | None:
        """Parse a single Habr article element into a dict."""
        # Title + URL
        title_el = item.select_one("a.tm-title__link")
        if title_el is None:
            return None
        title = title_el.get_text(strip=True)
        if not title:
            return None

        href = title_el.get("href", "")
        url = href if str(href).startswith("http") else f"https://habr.com{href}"

        # Article ID from URL: /articles/{id}/
        article_id = ""
        id_match = re.search(r"/articles/(\d+)", str(href))
        if id_match:
            article_id = id_match.group(1)
        if not article_id:
            return None

        pikabu_post_id = f"habr_{article_id}"

        # Body / description
        body_el = item.select_one(
            ".tm-article-body, .article-formatted-body"
        )
        body = body_el.get_text(strip=True) if body_el else ""

        # Published date
        time_el = item.select_one(
            "span.tm-article-datetime-published time[datetime], time[datetime]"
        )
        published_at = _parse_datetime(time_el)

        # Rating
        rating_el = item.select_one(".tm-votes-meter__value")
        rating = _parse_int(rating_el)

        # Comments count
        comments_el = item.select_one(
            ".tm-article-comments-counter-link__value"
        )
        comments_count = _parse_int(comments_el)

        return {
            "pikabu_post_id": pikabu_post_id,
            "title": title,
            "body": body,
            "published_at": published_at,
            "rating": rating,
            "comments_count": comments_count,
            "url": url,
        }

    @staticmethod
    def _extract_comments_from_html(html: str) -> list[dict]:
        """Extract comment data from a Habr article page HTML.

        CSS selectors:
        - Comment block: .tm-comment-thread__comment
        - Comment text: .tm-comment__body-content
        - Comment date: .tm-comment-datetime time[datetime]
        - Comment rating: .tm-votes-lever__score-count
        - Comment ID: from id attribute or data-comment-id
        """
        soup = BeautifulSoup(html, "html.parser")
        comments: list[dict] = []
        seen_ids: set[str] = set()

        comment_items = soup.select(".tm-comment-thread__comment")

        for item in comment_items:
            try:
                comment = HabrParserService._parse_single_comment(item)
                if (
                    comment is not None
                    and comment["pikabu_comment_id"] not in seen_ids
                ):
                    seen_ids.add(comment["pikabu_comment_id"])
                    comments.append(comment)
            except Exception:
                logger.warning(
                    "Failed to parse Habr comment element, skipping",
                    exc_info=True,
                )
                continue

        return comments

    @staticmethod
    def _parse_single_comment(item: Tag) -> dict | None:
        """Parse a single Habr comment element into a dict."""
        # Comment ID: from data-comment-id or id attribute
        comment_id = item.get("data-comment-id", "")
        if not comment_id:
            raw_id = item.get("id", "")
            if raw_id:
                # Extract numeric part from e.g. "comment_12345"
                m = re.search(r"(\d+)", str(raw_id))
                comment_id = m.group(1) if m else ""
        if not comment_id:
            return None

        pikabu_comment_id = f"habr_comment_{comment_id}"

        # Body
        body_el = item.select_one(".tm-comment__body-content")
        if body_el is None:
            return None
        body = body_el.get_text(strip=True)
        if not body:
            return None

        # Published date
        time_el = item.select_one(
            ".tm-comment-datetime time[datetime], time[datetime]"
        )
        published_at = _parse_datetime(time_el)

        # Rating
        rating_el = item.select_one(".tm-votes-lever__score-count")
        rating = _parse_int(rating_el)

        return {
            "pikabu_comment_id": pikabu_comment_id,
            "body": body,
            "published_at": published_at,
            "rating": rating,
        }

    # ------------------------------------------------------------------
    # HTTP fetching with retry logic (no proxy)
    # ------------------------------------------------------------------

    async def _fetch_page(self, url: str) -> str:
        """Fetch a single page with retry logic using curl_cffi.

        - HTTP 429: wait 60 seconds, then retry (up to 5 times).
        - HTTP 5xx: retry up to 3 times with 10s delay.
        - Network errors: retry up to 3 times with 15s delay.
        No proxy is used for Habr.
        """
        retries_5xx = 0
        retries_429 = 0
        retries_network = 0

        while True:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: curl_requests.get(
                        url,
                        headers=BROWSER_HEADERS,
                        impersonate="chrome",
                        timeout=30,
                        allow_redirects=True,
                    ),
                )

                if response.status_code == 429:
                    retries_429 += 1
                    if retries_429 > 5:
                        logger.error("HTTP 429 fetching %s — exhausted 5 retries", url)
                        raise HabrParserError(f"Habr rate limit: слишком много запросов к {url}")
                    logger.warning(
                        "HTTP 429 fetching %s — pausing %s s (attempt %d/5)",
                        url, RETRY_DELAY_429, retries_429,
                    )
                    await asyncio.sleep(RETRY_DELAY_429)
                    continue

                if 500 <= response.status_code < 600:
                    retries_5xx += 1
                    if retries_5xx <= RETRY_COUNT_5XX:
                        logger.warning(
                            "HTTP %s fetching %s — retry %s/%s in %s s",
                            response.status_code, url, retries_5xx,
                            RETRY_COUNT_5XX, RETRY_DELAY_5XX,
                        )
                        await asyncio.sleep(RETRY_DELAY_5XX)
                        continue
                    logger.error(
                        "HTTP %s fetching %s — exhausted %s retries",
                        response.status_code, url, RETRY_COUNT_5XX,
                    )

                if response.status_code >= 400:
                    logger.error("HTTP %s fetching %s", response.status_code, url)
                    raise HabrParserError(
                        f"HTTP {response.status_code} при загрузке {url}"
                    )

                retries_network = 0
                return response.text

            except HabrParserError:
                raise
            except Exception as exc:
                retries_network += 1
                if retries_network <= RETRY_COUNT_NETWORK:
                    logger.warning(
                        "Network error fetching %s: %s — retry %d/%d in %ds",
                        url, exc, retries_network, RETRY_COUNT_NETWORK,
                        RETRY_DELAY_NETWORK,
                    )
                    await asyncio.sleep(RETRY_DELAY_NETWORK)
                    continue
                logger.error("Network error fetching %s: %s — exhausted retries", url, exc)
                raise HabrParserError(
                    f"Сетевая ошибка при загрузке {url}: {exc}"
                ) from exc

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _get_topic(self, topic_id: int) -> Topic | None:
        result = await self._session.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        return result.scalar_one_or_none()

    async def _save_post(self, topic_id: int, post_data: dict) -> Post:
        """Insert or update a post in the database with source='habr'."""
        result = await self._session.execute(
            select(Post).where(Post.pikabu_post_id == post_data["pikabu_post_id"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.title = post_data["title"]
            existing.body = post_data["body"]
            existing.published_at = post_data["published_at"]
            existing.rating = post_data["rating"]
            existing.comments_count = post_data["comments_count"]
            existing.url = post_data["url"]
            existing.source = "habr"
            await self._session.execute(
                delete(Comment).where(Comment.post_id == existing.id)
            )
            await self._session.flush()
            return existing

        post = Post(
            topic_id=topic_id,
            pikabu_post_id=post_data["pikabu_post_id"],
            title=post_data["title"],
            body=post_data["body"],
            published_at=post_data["published_at"],
            rating=post_data["rating"],
            comments_count=post_data["comments_count"],
            url=post_data["url"],
            source="habr",
        )
        self._session.add(post)
        await self._session.flush()
        return post

    async def _save_comment(self, post_id: int, comment_data: dict) -> Comment:
        """Insert or update a comment in the database."""
        result = await self._session.execute(
            select(Comment).where(
                Comment.pikabu_comment_id == comment_data["pikabu_comment_id"]
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.body = comment_data["body"]
            existing.published_at = comment_data["published_at"]
            existing.rating = comment_data["rating"]
            await self._session.flush()
            return existing

        comment = Comment(
            post_id=post_id,
            pikabu_comment_id=comment_data["pikabu_comment_id"],
            body=comment_data["body"],
            published_at=comment_data["published_at"],
            rating=comment_data["rating"],
        )
        self._session.add(comment)
        await self._session.flush()
        return comment

    async def _update_parse_metadata(
        self, topic_id: int, posts_count: int, comments_count: int
    ) -> None:
        """Update or create parse metadata for the topic."""
        result = await self._session.execute(
            select(ParseMetadata).where(ParseMetadata.topic_id == topic_id)
        )
        existing = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if existing:
            existing.last_parsed_at = now
            existing.posts_count = posts_count
            existing.comments_count = comments_count
        else:
            meta = ParseMetadata(
                topic_id=topic_id,
                last_parsed_at=now,
                posts_count=posts_count,
                comments_count=comments_count,
            )
            self._session.add(meta)


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _parse_datetime(el: Tag | None) -> datetime:
    """Extract a datetime from a <time> element or return now(UTC)."""
    if el is None:
        return datetime.now(timezone.utc)

    dt_str = el.get("datetime", "") if isinstance(el, Tag) else ""
    if dt_str:
        # Python 3.11 doesn't support 'Z' suffix in fromisoformat
        dt_str = str(dt_str).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            pass

    return datetime.now(timezone.utc)


def _parse_int(el: Tag | None, attr: str | None = None) -> int:
    """Extract an integer from an element's text or attribute."""
    if el is None:
        return 0

    raw = ""
    if attr:
        raw = str(el.get(attr, ""))
    if not raw:
        raw = el.get_text(strip=True)

    cleaned = "".join(ch for ch in raw if ch.isdigit() or ch == "-")
    if not cleaned or cleaned == "-":
        return 0
    try:
        return int(cleaned)
    except ValueError:
        return 0
