"""ParserService — parses posts and comments from pikabu.ru."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Callable, Awaitable
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import httpx
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup, Tag
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import Post, Comment, ParseMetadata, Topic

logger = logging.getLogger(__name__)

# Type alias for progress callbacks
ProgressCallback = Callable[[str, int], Awaitable[None]] | None

PIKABU_BASE_URL = "https://pikabu.ru"
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


class ParserError(Exception):
    """Base error for ParserService operations."""


class ParserService:
    """Parses posts and comments from pikabu.ru for a given topic."""

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
        """Parse all posts for a topic from the last N days.

        Returns a dict with keys: posts_count, comments_count.
        """
        topic = await self._get_topic(topic_id)
        if topic is None:
            raise ParserError(f"Тема с id={topic_id} не найдена")

        if callback:
            await callback("parsing", 0)

        since = datetime.now(timezone.utc) - timedelta(days=days)
        posts_data = await self.parse_posts(topic.url, since)

        total_posts = len(posts_data)
        total_comments = 0

        for i, post_data in enumerate(posts_data):
            # Save post to DB
            db_post = await self._save_post(topic_id, post_data)

            # Parse and save comments for this post (skip on error, don't crash)
            try:
                comments_data = await self.parse_comments(post_data["url"])
                for comment_data in comments_data:
                    await self._save_comment(db_post.id, comment_data)
                total_comments += len(comments_data)
            except Exception as exc:
                logger.warning("Skipping comments for post %s: %s", post_data.get("pikabu_post_id", "?"), exc)

            if callback:
                progress = int(((i + 1) / total_posts) * 100) if total_posts > 0 else 100
                await callback("parsing", progress)

            # Delay between posts to avoid 429 rate limiting
            await asyncio.sleep(3)

        # Update parse metadata
        await self._update_parse_metadata(topic_id, total_posts, total_comments)
        await self._session.flush()

        return {"posts_count": total_posts, "comments_count": total_comments}

    async def parse_posts(self, topic_url: str, since: datetime) -> list[dict]:
        """Fetch and parse posts from a topic page, filtering to last 30 days.

        Returns a list of dicts with keys:
        title, body, published_at, rating, comments_count, url, pikabu_post_id
        """
        topic_url = _ensure_date_sort(topic_url)
        all_posts: list[dict] = []
        page = 1

        while True:
            page_url = f"{topic_url}&page={page}" if page > 1 else topic_url
            html = await self._fetch_page(page_url)
            logger.info("Page %d: %d chars HTML", page, len(html))
            posts = self._extract_posts_from_html(html)
            logger.info("Page %d: %d posts extracted", page, len(posts))

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
                    logger.info("Old post skipped: %s date=%s", post["pikabu_post_id"], post["published_at"])

            # Stop only when ALL posts on page are old (no fresh ones)
            if found_old and fresh_on_page == 0:
                logger.info("Stopping pagination: all posts on page %d are old. Total posts: %d", page, len(all_posts))
                break

            logger.info("Page %d done: %d fresh, %d old. Total so far: %d", page, fresh_on_page, len(posts) - fresh_on_page, len(all_posts))

            page += 1

        return all_posts

    async def parse_comments(self, post_url: str) -> list[dict]:
        """Fetch comments via pikabu's XML comments endpoint.

        Uses generate_xml_comm.php which returns all comments as XML.
        Falls back to page HTML parsing if XML endpoint fails.

        Returns a list of dicts with keys:
        body, published_at, rating, pikabu_comment_id
        """
        # Extract story ID from URL (last number after underscore)
        import re
        match = re.search(r'_(\d+)$', post_url.rstrip("/"))
        if not match:
            html = await self._fetch_page(post_url)
            return self._extract_comments_from_html(html)

        story_id = match.group(1)

        try:
            comments = await self._fetch_comments_xml(story_id)
            if comments:
                logger.info("Got %d comments via XML for story %s", len(comments), story_id)
                return comments
        except Exception as exc:
            logger.warning("XML comments failed for story %s: %s", story_id, exc)

        # Fallback to page HTML
        html = await self._fetch_page(post_url)
        return self._extract_comments_from_html(html)

    async def _fetch_comments_xml(self, story_id: str) -> list[dict]:
        """Fetch comments using pikabu's XML endpoint with retry on 429."""
        import xml.etree.ElementTree as ET

        proxy = settings.pikabu_proxy_url or None
        url = f"https://pikabu.ru/generate_xml_comm.php?id={story_id}"

        for attempt in range(3):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: curl_requests.get(
                        url,
                        headers={"User-Agent": USER_AGENT},
                        impersonate="chrome",
                        timeout=30,
                        allow_redirects=True,
                        proxy=proxy,
                    ),
                )
                if response.status_code == 429:
                    wait = 10 * (attempt + 1)
                    logger.warning("429 on XML comments for story %s, waiting %ds", story_id, wait)
                    await asyncio.sleep(wait)
                    continue
                if response.status_code >= 400:
                    raise Exception(f"HTTP {response.status_code}")
                break
            except Exception as exc:
                if attempt == 2:
                    raise
                wait = 10 * (attempt + 1)
                logger.warning("Error fetching XML comments for story %s: %s, waiting %ds", story_id, exc, wait)
                await asyncio.sleep(wait)
                continue
        else:
            return []

        root = ET.fromstring(response.text)
        comments: list[dict] = []

        for elem in root.findall("comment"):
            body_raw = elem.text or ""
            # Strip HTML tags from CDATA content
            body_soup = BeautifulSoup(body_raw, "html.parser")
            body = body_soup.get_text(strip=True)
            if not body:
                continue

            comment_id = elem.attrib.get("id", "")
            if not comment_id:
                continue

            # Parse date
            date_str = elem.attrib.get("date", "")
            try:
                published_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                published_at = published_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                published_at = datetime.now(timezone.utc)

            rating = 0
            try:
                rating = int(elem.attrib.get("rating", "0"))
            except (ValueError, TypeError):
                pass

            comments.append({
                "pikabu_comment_id": str(comment_id),
                "body": body,
                "published_at": published_at,
                "rating": rating,
            })

        return comments

    # ------------------------------------------------------------------
    # HTML parsing (static, testable without HTTP)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_posts_from_html(html: str) -> list[dict]:
        """Extract post data from a topic page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        posts: list[dict] = []
        seen_ids: set[str] = set()

        story_items = soup.select("article.story, div.story, [data-story-id]")

        for item in story_items:
            try:
                # Deduplicate by data-story-id
                story_id = item.get("data-story-id", "")
                if story_id and story_id in seen_ids:
                    continue

                post = ParserService._parse_single_post(item)
                if post is not None:
                    if post["pikabu_post_id"] in seen_ids:
                        continue
                    seen_ids.add(post["pikabu_post_id"])
                    if story_id:
                        seen_ids.add(story_id)
                    posts.append(post)
            except Exception:
                logger.warning("Failed to parse post element, skipping", exc_info=True)
                continue

        return posts

    @staticmethod
    def _parse_single_post(item: Tag) -> dict | None:
        """Parse a single post element into a dict."""
        # Title
        title_el = item.select_one(
            ".story__title-link, .story__title a, a.story__title-link"
        )
        if title_el is None:
            return None
        title = title_el.get_text(strip=True)

        # URL
        href = title_el.get("href", "")
        url = href if href.startswith("http") else f"{PIKABU_BASE_URL}{href}"

        # Post ID
        pikabu_post_id = (
            item.get("data-story-id", "")
            or url.rstrip("/").split("/")[-1]
            or ""
        )
        if not pikabu_post_id:
            return None

        # Body
        body_el = item.select_one(
            ".story__content-inner, .story__text, .story-block__text"
        )
        body = body_el.get_text(strip=True) if body_el else ""

        # Published date
        time_el = item.select_one("time[datetime], .story__datetime")
        published_at = _parse_datetime(time_el)

        # Rating
        rating_el = item.select_one(
            ".story__rating-count, .story__rating .score, [data-rating]"
        )
        rating = _parse_int(rating_el, attr="data-rating")

        # Comments count
        comments_el = item.select_one(
            ".story__comments-count, .story__comments a"
        )
        comments_count = _parse_int(comments_el)

        return {
            "pikabu_post_id": str(pikabu_post_id),
            "title": title,
            "body": body,
            "published_at": published_at,
            "rating": rating,
            "comments_count": comments_count,
            "url": url,
        }

    @staticmethod
    def _extract_comments_from_html(html: str) -> list[dict]:
        """Extract comment data from a post page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        comments: list[dict] = []

        comment_items = soup.select(
            ".comment, div.comment, [data-comment-id]"
        )

        for item in comment_items:
            try:
                comment = ParserService._parse_single_comment(item)
                if comment is not None:
                    comments.append(comment)
            except Exception:
                logger.warning("Failed to parse comment element, skipping", exc_info=True)
                continue

        return comments

    @staticmethod
    def _parse_single_comment(item: Tag) -> dict | None:
        """Parse a single comment element into a dict."""
        # Comment ID
        pikabu_comment_id = item.get("data-comment-id", "")
        if not pikabu_comment_id:
            id_el = item.get("id", "")
            pikabu_comment_id = id_el.replace("comment_", "") if id_el else ""
        if not pikabu_comment_id:
            return None

        # Body
        body_el = item.select_one(
            ".comment__content, .comment__text, .comment-content__text"
        )
        if body_el is None:
            return None
        body = body_el.get_text(strip=True)
        if not body:
            return None

        # Published date
        time_el = item.select_one("time[datetime], .comment__datetime")
        published_at = _parse_datetime(time_el)

        # Rating
        rating_el = item.select_one(
            ".comment__rating-count, .comment__rating .score, [data-rating]"
        )
        rating = _parse_int(rating_el, attr="data-rating")

        return {
            "pikabu_comment_id": str(pikabu_comment_id),
            "body": body,
            "published_at": published_at,
            "rating": rating,
        }

    # ------------------------------------------------------------------
    # HTTP fetching with retry logic
    # ------------------------------------------------------------------

    async def _fetch_page(self, url: str) -> str:
        """Fetch a single page with retry logic using curl_cffi.

        Uses Chrome TLS fingerprint impersonation for anti-bot bypass.

        - HTTP 429: wait ``settings.pikabu_retry_delay_429`` seconds, then retry.
        - HTTP 5xx: retry up to ``settings.pikabu_retry_count_5xx`` times with
          ``settings.pikabu_retry_delay_5xx`` seconds between attempts.
        - Network errors: raise ``ParserError`` immediately.
        """
        retries_5xx = 0
        retries_429 = 0
        proxy = settings.pikabu_proxy_url or None

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
                        proxy=proxy,
                    ),
                )

                if response.status_code == 429:
                    retries_429 += 1
                    if retries_429 > 5:
                        logger.error("HTTP 429 fetching %s — exhausted 5 retries", url)
                        raise ParserError(f"Pikabu rate limit: слишком много запросов к {url}")
                    logger.warning(
                        "HTTP 429 fetching %s — pausing %s s (attempt %d/5)",
                        url,
                        settings.pikabu_retry_delay_429,
                        retries_429,
                    )
                    await asyncio.sleep(settings.pikabu_retry_delay_429)
                    continue

                if 500 <= response.status_code < 600:
                    retries_5xx += 1
                    if retries_5xx <= settings.pikabu_retry_count_5xx:
                        logger.warning(
                            "HTTP %s fetching %s — retry %s/%s in %s s",
                            response.status_code,
                            url,
                            retries_5xx,
                            settings.pikabu_retry_count_5xx,
                            settings.pikabu_retry_delay_5xx,
                        )
                        await asyncio.sleep(settings.pikabu_retry_delay_5xx)
                        continue

                    logger.error(
                        "HTTP %s fetching %s — exhausted %s retries",
                        response.status_code,
                        url,
                        settings.pikabu_retry_count_5xx,
                    )

                if response.status_code >= 400:
                    logger.error("HTTP %s fetching %s", response.status_code, url)
                    raise ParserError(
                        f"HTTP {response.status_code} при загрузке {url}"
                    )

                return response.text

            except ParserError:
                raise
            except Exception as exc:
                logger.error("Network error fetching %s: %s", url, exc)
                raise ParserError(
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
        """Insert or update a post in the database. Returns the Post object."""
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
            # Delete old comments so they get replaced with fresh ones
            from sqlalchemy import delete
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


def _ensure_date_sort(url: str) -> str:
    """Ensure the URL contains the query parameter ``sort=date``."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params["sort"] = ["date"]
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _parse_datetime(el: Tag | None) -> datetime:
    """Extract a datetime from a <time> element or return now(UTC)."""
    if el is None:
        return datetime.now(timezone.utc)

    dt_str = el.get("datetime", "") if isinstance(el, Tag) else ""
    if dt_str:
        try:
            return datetime.fromisoformat(str(dt_str))
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

    # Remove non-digit chars except minus sign
    cleaned = "".join(ch for ch in raw if ch.isdigit() or ch == "-")
    if not cleaned or cleaned == "-":
        return 0
    try:
        return int(cleaned)
    except ValueError:
        return 0
