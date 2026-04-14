"""TopicManager — fetches and caches Pikabu communities/tags."""

import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import Topic

logger = logging.getLogger(__name__)

PIKABU_COMMUNITIES_URL = "https://pikabu.ru/communities"

# Pikabu renders /communities via JavaScript, so BeautifulSoup gets empty HTML.
# Fallback: popular communities list (can be extended).
FALLBACK_COMMUNITIES = [
    {"pikabu_id": "science", "name": "Наука", "url": "https://pikabu.ru/community/science", "subscribers_count": None},
    {"pikabu_id": "politika", "name": "Политика", "url": "https://pikabu.ru/community/politika", "subscribers_count": None},
    {"pikabu_id": "auto", "name": "Авто", "url": "https://pikabu.ru/community/auto", "subscribers_count": None},
    {"pikabu_id": "humor", "name": "Юмор", "url": "https://pikabu.ru/community/humor", "subscribers_count": None},
    {"pikabu_id": "history", "name": "История", "url": "https://pikabu.ru/community/history", "subscribers_count": None},
    {"pikabu_id": "serials", "name": "Кино и сериалы", "url": "https://pikabu.ru/community/serials", "subscribers_count": None},
    {"pikabu_id": "sport", "name": "Спорт", "url": "https://pikabu.ru/community/sport", "subscribers_count": None},
    {"pikabu_id": "zoo", "name": "Животные", "url": "https://pikabu.ru/community/zoo", "subscribers_count": None},
    {"pikabu_id": "eda", "name": "Еда", "url": "https://pikabu.ru/community/eda", "subscribers_count": None},
    {"pikabu_id": "music", "name": "Музыка", "url": "https://pikabu.ru/community/music", "subscribers_count": None},
    {"pikabu_id": "travel", "name": "Путешествия", "url": "https://pikabu.ru/community/travel", "subscribers_count": None},
    {"pikabu_id": "diy", "name": "Сделай сам", "url": "https://pikabu.ru/community/diy", "subscribers_count": None},
    {"pikabu_id": "books", "name": "Книги", "url": "https://pikabu.ru/community/books", "subscribers_count": None},
    {"pikabu_id": "space", "name": "Космос", "url": "https://pikabu.ru/community/space", "subscribers_count": None},
    {"pikabu_id": "psychology", "name": "Психология", "url": "https://pikabu.ru/community/psychology", "subscribers_count": None},
    {"pikabu_id": "economy", "name": "Экономика", "url": "https://pikabu.ru/community/economy", "subscribers_count": None},
    {"pikabu_id": "medicina", "name": "Медицина", "url": "https://pikabu.ru/community/medicina", "subscribers_count": None},
    {"pikabu_id": "education", "name": "Образование", "url": "https://pikabu.ru/community/education", "subscribers_count": None},
    {"pikabu_id": "EnglishPikabu", "name": "English Pikabu", "url": "https://pikabu.ru/community/EnglishPikabu", "subscribers_count": None},
    {"pikabu_id": "enginphrases", "name": "Английский в фразах", "url": "https://pikabu.ru/community/enginphrases", "subscribers_count": None},
]


class TopicManagerError(Exception):
    """Base error for TopicManager operations."""


def filter_topics(topics: list[Topic], search: str) -> list[Topic]:
    """Filter topics whose name contains *search* (case-insensitive).

    If *search* is empty, all topics are returned unchanged.
    """
    if not search:
        return list(topics)
    search_lower = search.lower()
    return [t for t in topics if search_lower in t.name.lower()]


class TopicManager:
    """Loads and caches the list of available Pikabu communities/tags."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def filter_topics(topics: list[Topic], search: str) -> list[Topic]:
        """Filter topics by name substring (case-insensitive).

        Delegates to the module-level :func:`filter_topics` function.
        """
        return filter_topics(topics, search)

    async def fetch_topics(self) -> list[Topic]:
        """Fetch communities from pikabu.ru, cache them in DB, and return."""
        cached = await self._get_cached_topics()
        if cached is not None:
            return cached

        raw_topics = await self._scrape_communities()
        await self._upsert_topics(raw_topics)
        await self._session.commit()
        return await self._all_topics()

    async def get_topic_info(self, topic_id: int) -> Topic | None:
        """Return a single topic by its DB primary key, or None."""
        result = await self._session.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    async def _get_cached_topics(self) -> list[Topic] | None:
        """Return cached topics if any exist and are fresh enough."""
        topics = await self._all_topics()
        if not topics:
            return None

        now = datetime.now(timezone.utc)
        oldest_fetch = min(
            (t.last_fetched_at for t in topics if t.last_fetched_at is not None),
            default=None,
        )
        if oldest_fetch is None:
            return None

        hours_since = (now - oldest_fetch).total_seconds() / 3600
        if hours_since < settings.cache_ttl_hours:
            return topics
        return None

    async def _all_topics(self) -> list[Topic]:
        result = await self._session.execute(select(Topic).order_by(Topic.name))
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Scraping
    # ------------------------------------------------------------------

    async def _scrape_communities(self) -> list[dict]:
        """Scrape the communities page and return raw dicts.

        Pikabu renders /communities via JavaScript, so HTML parsing may
        return an empty list. In that case, fall back to a curated list.
        """
        try:
            proxy = settings.pikabu_proxy_url or None
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                proxy=proxy,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                },
            ) as client:
                response = await client.get(PIKABU_COMMUNITIES_URL)
                response.raise_for_status()

            parsed = self._parse_communities_html(response.text)
            if parsed:
                return parsed

            logger.info("HTML parsing returned 0 communities, using fallback list")
            return list(FALLBACK_COMMUNITIES)

        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning("Failed to fetch pikabu communities: %s — using fallback", exc)
            return list(FALLBACK_COMMUNITIES)

    @staticmethod
    def _parse_communities_html(html: str) -> list[dict]:
        """Extract community data from the HTML page."""
        soup = BeautifulSoup(html, "html.parser")
        topics: list[dict] = []

        community_items = soup.select(".communities-item, .community-item")
        if not community_items:
            community_items = soup.select("[data-community-id]")

        for item in community_items:
            link = item.select_one("a[href]")
            name_el = item.select_one(
                ".communities-item__title, .community-item__title, .community__title"
            )
            subs_el = item.select_one(
                ".communities-item__subscribers, "
                ".community-item__subscribers, "
                ".community__subscribers-count"
            )

            if not link or not name_el:
                continue

            href = link.get("href", "")
            url = href if href.startswith("http") else f"https://pikabu.ru{href}"
            name = name_el.get_text(strip=True)

            pikabu_id = item.get("data-community-id", "") or href.rstrip("/").split("/")[-1]

            subscribers_count = None
            if subs_el:
                raw = subs_el.get_text(strip=True).replace("\xa0", "").replace(" ", "")
                digits = "".join(ch for ch in raw if ch.isdigit())
                if digits:
                    subscribers_count = int(digits)

            topics.append(
                {
                    "pikabu_id": str(pikabu_id),
                    "name": name,
                    "url": url,
                    "subscribers_count": subscribers_count,
                }
            )

        return topics

    # ------------------------------------------------------------------
    # DB upsert
    # ------------------------------------------------------------------

    async def _upsert_topics(self, raw_topics: list[dict]) -> None:
        """Insert or update topics in the database."""
        now = datetime.now(timezone.utc)

        for raw in raw_topics:
            result = await self._session.execute(
                select(Topic).where(Topic.pikabu_id == raw["pikabu_id"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.name = raw["name"]
                existing.url = raw["url"]
                existing.subscribers_count = raw["subscribers_count"]
                existing.last_fetched_at = now
            else:
                topic = Topic(
                    pikabu_id=raw["pikabu_id"],
                    name=raw["name"],
                    url=raw["url"],
                    subscribers_count=raw["subscribers_count"],
                    last_fetched_at=now,
                )
                self._session.add(topic)

        await self._session.flush()
