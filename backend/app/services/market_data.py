"""Service for enriching MarketTrend entries with real market data from external sources."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import settings
from app.models.schemas import MarketTrend

logger = logging.getLogger(__name__)

FALLBACK_LABEL = "Оценка ИИ (реальные данные недоступны)"


class MarketDataService:
    """Enriches MarketTrend entries with real market data from external sources."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float | None = None,
    ):
        self.api_key = api_key or settings.serpapi_key
        self.timeout = timeout if timeout is not None else settings.enrichment_per_source_timeout

    async def enrich_trends(
        self,
        trends: list[MarketTrend],
        total_timeout: float | None = None,
    ) -> list[MarketTrend]:
        """
        Enrich each trend with market_volume_estimate and growth_rate_percent.
        Falls back to LLM label if timeout or API error.

        Args:
            trends: List of MarketTrend objects to enrich.
            total_timeout: Total time budget for all enrichment (seconds).

        Returns:
            The same list of MarketTrend objects with enriched fields populated.
        """
        if total_timeout is None:
            total_timeout = settings.enrichment_total_timeout

        if not self.api_key:
            # No API key configured — apply fallback to all trends
            logger.warning("No SerpAPI key configured, applying fallback to all trends")
            for trend in trends:
                trend.data_source_label = FALLBACK_LABEL
            return trends

        try:
            enriched = await asyncio.wait_for(
                self._enrich_all(trends),
                timeout=total_timeout,
            )
            return enriched
        except asyncio.TimeoutError:
            logger.warning(
                "Total enrichment timeout (%.1fs) exceeded, applying fallback to remaining trends",
                total_timeout,
            )
            # Apply fallback to any trends not yet enriched
            for trend in trends:
                if trend.market_volume_estimate is None and trend.data_source_label is None:
                    trend.data_source_label = FALLBACK_LABEL
            return trends

    async def _enrich_all(self, trends: list[MarketTrend]) -> list[MarketTrend]:
        """Enrich all trends sequentially (to respect rate limits)."""
        for trend in trends:
            try:
                await self._enrich_single(trend)
            except Exception as exc:
                logger.warning(
                    "Failed to enrich trend '%s': %s", trend.name, exc
                )
                trend.data_source_label = FALLBACK_LABEL
        return trends

    async def _enrich_single(self, trend: MarketTrend) -> None:
        """Enrich a single MarketTrend with external data."""
        # Derive up to 5 keywords from trend name and description
        keywords = self._extract_keywords(trend.name, trend.description)

        data = await self._query_trend_data(keywords)

        if data is None:
            trend.data_source_label = FALLBACK_LABEL
            return

        # Populate enriched fields
        volume = data.get("market_volume_estimate")
        nominal_growth = data.get("growth_rate_percent")

        if volume is not None:
            trend.market_volume_estimate = volume

        if nominal_growth is not None:
            trend.growth_rate_percent = self._adjust_for_inflation(
                nominal_growth, settings.inflation_rate_percent
            )

        # If we got at least some data, clear fallback label
        if trend.market_volume_estimate is not None or trend.growth_rate_percent is not None:
            trend.data_source_label = None
        else:
            trend.data_source_label = FALLBACK_LABEL

    async def _query_trend_data(self, keywords: list[str]) -> dict[str, Any] | None:
        """
        Query Google Trends / SerpAPI for volume and growth data.

        Args:
            keywords: Up to 5 search keywords derived from the trend.

        Returns:
            Dict with 'market_volume_estimate' and/or 'growth_rate_percent',
            or None if the query fails.
        """
        if not keywords:
            return None

        query = ",".join(keywords[:5])
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_trends",
            "q": query,
            "api_key": self.api_key,
            "data_type": "TIMESERIES",
            "date": "today 12-m",  # Last 12 months for YoY calculation
        }

        try:
            data = await self._make_request(url, params)
            if data is None:
                return None
            return self._parse_serpapi_response(data)
        except Exception as exc:
            logger.warning("SerpAPI query failed for keywords %s: %s", keywords, exc)
            return None

    async def _make_request(
        self, url: str, params: dict[str, str]
    ) -> dict[str, Any] | None:
        """
        Make HTTP request with single exponential backoff retry on rate limit (429).

        Returns parsed JSON response or None on failure.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params)

                if response.status_code == 429:
                    # Rate limited — single retry with exponential backoff
                    retry_after = float(
                        response.headers.get("Retry-After", "2")
                    )
                    wait_time = min(retry_after * 2, self.timeout / 2)
                    logger.info(
                        "Rate limited (429), retrying after %.1fs", wait_time
                    )
                    await asyncio.sleep(wait_time)

                    response = await client.get(url, params=params)
                    if response.status_code != 200:
                        logger.warning(
                            "SerpAPI retry failed with status %d",
                            response.status_code,
                        )
                        return None

                if response.status_code != 200:
                    logger.warning(
                        "SerpAPI returned status %d", response.status_code
                    )
                    return None

                return response.json()

            except httpx.TimeoutException:
                logger.warning("SerpAPI request timed out (%.1fs)", self.timeout)
                return None
            except httpx.HTTPError as exc:
                logger.warning("HTTP error querying SerpAPI: %s", exc)
                return None

    def _parse_serpapi_response(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Parse SerpAPI Google Trends response to extract volume and growth.

        Returns dict with market_volume_estimate and/or growth_rate_percent,
        or None if response is unparseable.
        """
        result: dict[str, Any] = {}

        try:
            # Extract interest over time data for growth calculation
            interest_over_time = data.get("interest_over_time", {})
            timeline_data = interest_over_time.get("timeline_data", [])

            if timeline_data and len(timeline_data) >= 2:
                # Calculate YoY growth from first vs last data points
                first_values = timeline_data[0].get("values", [])
                last_values = timeline_data[-1].get("values", [])

                if first_values and last_values:
                    first_val = int(first_values[0].get("extracted_value", 0))
                    last_val = int(last_values[0].get("extracted_value", 0))

                    if first_val > 0:
                        growth_pct = ((last_val - first_val) / first_val) * 100
                        result["growth_rate_percent"] = round(growth_pct, 1)

            # Extract related queries for volume estimation
            related_queries = data.get("related_queries", {})
            rising = related_queries.get("rising", [])

            # Use search volume from related queries if available
            if rising:
                # Sum search volumes as a rough proxy for market interest
                total_volume = sum(
                    int(q.get("extracted_value", 0))
                    for q in rising
                    if q.get("extracted_value")
                )
                if total_volume > 0:
                    # Convert to estimated market volume (rough proxy)
                    # Format as readable string
                    result["market_volume_estimate"] = self._format_volume(total_volume)

        except (KeyError, ValueError, TypeError, IndexError) as exc:
            logger.debug("Error parsing SerpAPI response: %s", exc)

        return result if result else None

    def _adjust_for_inflation(
        self, nominal_rate: float, inflation_rate: float
    ) -> float:
        """
        Subtract inflation from nominal growth to get real growth rate.

        Args:
            nominal_rate: Nominal year-over-year growth percentage.
            inflation_rate: Annual inflation rate percentage.

        Returns:
            Real growth rate = nominal_rate - inflation_rate.
        """
        return nominal_rate - inflation_rate

    def _extract_keywords(self, name: str, description: str) -> list[str]:
        """
        Extract up to 5 meaningful keywords from trend name and description.

        Args:
            name: Trend name.
            description: Trend description.

        Returns:
            List of up to 5 keyword strings.
        """
        # Combine name and description, split into words
        combined = f"{name} {description}"
        # Remove common short words and punctuation
        stop_words = {
            "и", "в", "на", "с", "по", "для", "от", "до", "из", "к", "о",
            "не", "что", "это", "как", "а", "но", "или", "the", "and", "of",
            "in", "to", "for", "is", "are", "a", "an", "at", "by", "with",
        }

        words = []
        for word in combined.split():
            # Strip punctuation
            cleaned = word.strip(".,;:!?()[]{}\"'—–-")
            if cleaned and len(cleaned) > 2 and cleaned.lower() not in stop_words:
                words.append(cleaned)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_words: list[str] = []
        for w in words:
            lower = w.lower()
            if lower not in seen:
                seen.add(lower)
                unique_words.append(w)

        return unique_words[:5]

    @staticmethod
    def _format_volume(raw_value: int) -> str:
        """
        Format a raw numeric value into a human-readable market volume string.

        Uses Russian number formatting with magnitude suffixes.
        """
        if raw_value >= 1_000_000_000:
            return f"~{raw_value / 1_000_000_000:.1f} млрд ₽"
        elif raw_value >= 1_000_000:
            return f"~{raw_value / 1_000_000:.0f} млн ₽"
        elif raw_value >= 1_000:
            return f"~{raw_value / 1_000:.0f} тыс ₽"
        else:
            return f"~{raw_value} ₽"
