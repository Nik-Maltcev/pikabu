"""
CompetitorLookupService — поиск аналогичных бизнесов через Linkup API.

Для каждой BusinessIdea ищет 1-3 аналога с информацией о выручке,
инвестиционных раундах и наличии конкурентов в РФ.

Graceful degradation:
- Timeout/network error → analogues = [] (frontend shows fallback message)
- No results found → analogues = [] (frontend shows positive signal)
"""

import asyncio
import logging

import httpx

from app.config import settings
from app.models.schemas import Analogue, BusinessIdea

logger = logging.getLogger(__name__)

# Linkup API base URL
LINKUP_API_URL = "https://api.linkup.so/v1/search"


class CompetitorLookupService:
    """Finds analogous businesses for each BusinessIdea via external APIs."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float | None = None,
    ):
        self.api_key = api_key or settings.linkup_api_key
        self.timeout = timeout if timeout is not None else settings.enrichment_per_source_timeout

    async def find_analogues(
        self,
        ideas: list[BusinessIdea],
        total_timeout: float | None = None,
    ) -> list[BusinessIdea]:
        """
        For each idea, find 1-3 analogous businesses.
        Populates idea.analogues list.

        Falls back gracefully:
        - On timeout/network error: analogues = [] (frontend shows error message)
        - On no results: analogues = [] (frontend shows positive "market may be empty")

        Args:
            ideas: List of BusinessIdea objects to enrich.
            total_timeout: Total time budget for all lookups (default from settings).

        Returns:
            The same list of BusinessIdea objects with analogues populated.
        """
        if total_timeout is None:
            total_timeout = settings.enrichment_total_timeout

        if not self.api_key:
            logger.warning("Linkup API key not configured, skipping competitor lookup")
            return ideas

        try:
            async with asyncio.timeout(total_timeout):
                tasks = [
                    self._enrich_idea(idea)
                    for idea in ideas
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
        except TimeoutError:
            logger.warning(
                f"Competitor lookup total timeout ({total_timeout}s) exceeded, "
                f"some ideas may not have analogues"
            )

        return ideas

    async def _enrich_idea(self, idea: BusinessIdea) -> None:
        """Search for analogues for a single idea and populate its analogues list."""
        try:
            analogues = await self._search_competitors(idea.name, idea.description)
            idea.analogues = analogues
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as e:
            logger.warning(
                f"Competitor lookup failed for '{idea.name}': {type(e).__name__}: {e}"
            )
            idea.analogues = []
        except Exception as e:
            logger.error(
                f"Unexpected error during competitor lookup for '{idea.name}': {e}"
            )
            idea.analogues = []

    async def _search_competitors(
        self, idea_name: str, description: str
    ) -> list[Analogue]:
        """
        Search Linkup API for competitors matching the idea,
        then extract structured company data via LLM.

        Args:
            idea_name: Name of the business idea.
            description: Description of the business idea.

        Returns:
            List of 0-3 Analogue objects found.
        """
        query = f"российские стартапы и компании аналоги: {idea_name}. {description}. выручка, инвестиции, раунды"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                LINKUP_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "q": query,
                    "depth": "standard",
                    "outputType": "searchResults",
                },
            )

            if response.status_code == 429:
                # Rate limited — single retry with backoff
                logger.warning("Linkup API rate limited (429), retrying once after 2s")
                await asyncio.sleep(2)
                response = await client.post(
                    LINKUP_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "q": query,
                        "depth": "standard",
                        "outputType": "searchResults",
                    },
                )

            if response.status_code != 200:
                logger.warning(
                    f"Linkup API returned {response.status_code} for '{idea_name}'"
                )
                return []

            data = response.json()
            return await self._extract_analogues_via_llm(data, idea_name, description)

    async def _extract_analogues_via_llm(
        self, search_data: dict, idea_name: str, description: str
    ) -> list[Analogue]:
        """Extract structured company analogues from raw search results using LLM."""
        import json
        from app.services.analyzer import AnalyzerService

        results = search_data.get("results", [])
        if not results:
            return []

        # Build context from search results
        context_parts = []
        for i, result in enumerate(results[:5], 1):
            title = result.get("name", "") or result.get("title", "")
            content = result.get("content", "") or result.get("snippet", "")
            url = result.get("url", "")
            context_parts.append(f"{i}. {title}\n{content[:300]}\nURL: {url}")

        search_context = "\n\n".join(context_parts)

        prompt = f"""На основе результатов поиска ниже, найди 1-3 КОНКРЕТНЫЕ компании или стартапы, которые являются аналогами бизнес-идеи "{idea_name}" ({description}).

Результаты поиска:
{search_context}

Для каждой компании укажи:
- company_name: точное название компании
- description: что делает (1-2 предложения, до 150 символов)
- annual_revenue: годовая выручка если известна (строка, например "500 млн ₽" или null)
- investment_round: раунд инвестиций если известен (например "Series A, $10M" или null)
- has_ru_competitor: есть ли этот бизнес в России (true/false/null)

Ответь ТОЛЬКО валидным JSON массивом. Если конкретных компаний не нашлось — верни [].
Не выдумывай данные, указывай только то, что есть в результатах.

JSON:"""

        try:
            analyzer = AnalyzerService()
            response_text = await analyzer._call_llm(prompt, max_tokens=1000)
            
            # Parse JSON response
            response_text = response_text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]
            
            parsed = json.loads(response_text)
            if not isinstance(parsed, list):
                return []

            analogues: list[Analogue] = []
            for item in parsed[:3]:
                name = item.get("company_name", "")
                if not name:
                    continue
                desc = item.get("description", "")
                if len(desc) > 200:
                    desc = desc[:197] + "..."
                
                analogues.append(Analogue(
                    company_name=name,
                    description=desc,
                    annual_revenue=item.get("annual_revenue"),
                    investment_round=item.get("investment_round"),
                    has_ru_competitor=item.get("has_ru_competitor"),
                ))
            
            return analogues
        except Exception as e:
            logger.warning(f"LLM extraction of analogues failed for '{idea_name}': {e}")
            return []
