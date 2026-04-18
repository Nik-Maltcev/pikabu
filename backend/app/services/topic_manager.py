"""TopicManager — fetches and caches Pikabu communities/tags and Habr flows."""

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

# Predefined Habr flows (management, top_management, marketing)
HABR_FLOWS = [
    {"pikabu_id": "habr_management", "name": "Менеджмент", "url": "https://habr.com/ru/flows/management/articles/", "subscribers_count": None, "source": "habr"},
    {"pikabu_id": "habr_top_management", "name": "Топ-менеджмент", "url": "https://habr.com/ru/flows/top_management/articles/", "subscribers_count": None, "source": "habr"},
    {"pikabu_id": "habr_marketing", "name": "Маркетинг", "url": "https://habr.com/ru/flows/marketing/articles/", "subscribers_count": None, "source": "habr"},
]

# Pikabu renders /communities via JavaScript, so BeautifulSoup gets empty HTML.
# Fallback: popular communities list (can be extended).
FALLBACK_COMMUNITIES = [
    {"pikabu_id": "politics", "name": "Политика", "url": "https://pikabu.ru/themes/politics", "subscribers_count": None},
    {"pikabu_id": "adult", "name": "18+", "url": "https://pikabu.ru/themes/adult", "subscribers_count": None},
    {"pikabu_id": "games", "name": "Игры", "url": "https://pikabu.ru/themes/games", "subscribers_count": None},
    {"pikabu_id": "humor", "name": "Юмор", "url": "https://pikabu.ru/themes/humor", "subscribers_count": None},
    {"pikabu_id": "relationships", "name": "Отношения", "url": "https://pikabu.ru/themes/relationships", "subscribers_count": None},
    {"pikabu_id": "health", "name": "Здоровье", "url": "https://pikabu.ru/themes/health", "subscribers_count": None},
    {"pikabu_id": "travel", "name": "Путешествия", "url": "https://pikabu.ru/themes/travel", "subscribers_count": None},
    {"pikabu_id": "sport", "name": "Спорт", "url": "https://pikabu.ru/themes/sport", "subscribers_count": None},
    {"pikabu_id": "hobby", "name": "Хобби", "url": "https://pikabu.ru/themes/hobby", "subscribers_count": None},
    {"pikabu_id": "service", "name": "Сервис", "url": "https://pikabu.ru/themes/service", "subscribers_count": None},
    {"pikabu_id": "nature", "name": "Природа", "url": "https://pikabu.ru/themes/nature", "subscribers_count": None},
    {"pikabu_id": "business", "name": "Бизнес", "url": "https://pikabu.ru/themes/business", "subscribers_count": None},
    {"pikabu_id": "transport", "name": "Транспорт", "url": "https://pikabu.ru/themes/transport", "subscribers_count": None},
    {"pikabu_id": "talk", "name": "Общение", "url": "https://pikabu.ru/themes/talk", "subscribers_count": None},
    {"pikabu_id": "law", "name": "Юриспруденция", "url": "https://pikabu.ru/themes/law", "subscribers_count": None},
    {"pikabu_id": "science", "name": "Наука", "url": "https://pikabu.ru/themes/science", "subscribers_count": None},
    {"pikabu_id": "it", "name": "IT", "url": "https://pikabu.ru/themes/it", "subscribers_count": None},
    {"pikabu_id": "animals", "name": "Животные", "url": "https://pikabu.ru/themes/animals", "subscribers_count": None},
    {"pikabu_id": "cinema", "name": "Кино и сериалы", "url": "https://pikabu.ru/themes/cinema", "subscribers_count": None},
    {"pikabu_id": "economics", "name": "Экономика", "url": "https://pikabu.ru/themes/economics", "subscribers_count": None},
    {"pikabu_id": "cooking", "name": "Кулинария", "url": "https://pikabu.ru/themes/cooking", "subscribers_count": None},
    {"pikabu_id": "history", "name": "История", "url": "https://pikabu.ru/themes/history", "subscribers_count": None},
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

    async def fetch_topics(self, source: str = "pikabu") -> list[Topic]:
        """Fetch topics filtered by source.

        Args:
            source: "pikabu" (default), "habr", or "both".
        """
        if source in ("pikabu", "both"):
            cached_pikabu = await self._get_cached_topics(source="pikabu")
            if cached_pikabu is None:
                raw_topics = await self._scrape_communities()
                await self._upsert_topics(raw_topics, source="pikabu")
                await self._session.commit()

        if source in ("habr", "both"):
            cached_habr = await self._get_cached_topics(source="habr")
            if cached_habr is None:
                await self._upsert_topics(HABR_FLOWS, source="habr")
                await self._session.commit()

        return await self._all_topics(source=source)

    async def get_topic_info(self, topic_id: int) -> Topic | None:
        """Return a single topic by its DB primary key, or None."""
        result = await self._session.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    async def _get_cached_topics(self, source: str = "pikabu") -> list[Topic] | None:
        """Return cached topics if any exist and are fresh enough, filtered by source."""
        topics = await self._all_topics(source=source)
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

    async def _all_topics(self, source: str = "pikabu") -> list[Topic]:
        query = select(Topic).order_by(Topic.name)
        if source == "pikabu":
            query = query.where(Topic.source == "pikabu")
        elif source == "habr":
            query = query.where(Topic.source == "habr")
        # "both" — no filter, return all
        result = await self._session.execute(query)
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

    async def _upsert_topics(self, raw_topics: list[dict], source: str = "pikabu") -> None:
        """Insert or update topics in the database."""
        now = datetime.now(timezone.utc)

        for raw in raw_topics:
            result = await self._session.execute(
                select(Topic).where(Topic.pikabu_id == raw["pikabu_id"])
            )
            existing = result.scalar_one_or_none()

            topic_source = raw.get("source", source)

            if existing:
                existing.name = raw["name"]
                existing.url = raw["url"]
                existing.subscribers_count = raw["subscribers_count"]
                existing.source = topic_source
                existing.last_fetched_at = now
            else:
                topic = Topic(
                    pikabu_id=raw["pikabu_id"],
                    name=raw["name"],
                    url=raw["url"],
                    subscribers_count=raw["subscribers_count"],
                    source=topic_source,
                    last_fetched_at=now,
                )
                self._session.add(topic)

        await self._session.flush()
