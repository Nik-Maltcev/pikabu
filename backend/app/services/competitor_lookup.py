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
        # HTTP timeout is for Linkup API call only (LLM has its own timeout)
        self.timeout = min(timeout or settings.enrichment_per_source_timeout, 15.0)

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
        except (TimeoutError, asyncio.TimeoutError):
            logger.warning(
                f"Competitor lookup total timeout ({total_timeout}s) exceeded, "
                f"some ideas may not have analogues"
            )
        except Exception as e:
            logger.error(f"Competitor lookup unexpected error: {e}", exc_info=True)

        return ideas

    async def _enrich_idea(self, idea: BusinessIdea) -> None:
        """Search for analogues for a single idea and populate its analogues list."""
        try:
            logger.info(f"Competitor lookup starting for '{idea.name}'")
            analogues = await self._search_competitors(idea.name, idea.description)
            idea.analogues = analogues
            logger.info(f"Competitor lookup for '{idea.name}': found {len(analogues)} analogues")
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as e:
            logger.warning(
                f"Competitor lookup failed for '{idea.name}': {type(e).__name__}: {e}"
            )
            idea.analogues = []
        except asyncio.TimeoutError:
            logger.warning(f"Competitor lookup timed out for '{idea.name}'")
            idea.analogues = []
        except Exception as e:
            logger.error(
                f"Unexpected error during competitor lookup for '{idea.name}': {e}",
                exc_info=True
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
        query = f"{idea_name} стартап компания конкуренты выручка инвестиции"

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
        """Extract structured company analogues using LLM with search results as context."""
        import json
        from app.services.analyzer import AnalyzerService

        results = search_data.get("results", [])

        # Build context from search results (may be empty — LLM will use its own knowledge)
        context_parts = []
        for i, result in enumerate(results[:7], 1):
            title = result.get("name", "") or result.get("title", "")
            content = result.get("content", "") or result.get("snippet", "")
            context_parts.append(f"{i}. {title}: {content[:300]}")

        search_context = "\n".join(context_parts) if context_parts else "Нет результатов поиска."

        prompt = f"""Из результатов поиска ниже извлеки ТОЛЬКО те компании/стартапы, которые ЯВНО УПОМИНАЮТСЯ в тексте и работают в нише "{idea_name}" ({description}).

Результаты поиска:
{search_context}

СТРОГИЕ ПРАВИЛА:
- Называй ТОЛЬКО компании, которые ПРЯМО УПОМЯНУТЫ в тексте выше
- НЕ ПРИДУМЫВАЙ компании из своих знаний
- Если в тексте нет конкретных названий компаний — верни пустой массив []
- Для выручки и раундов указывай ТОЛЬКО то, что написано в тексте (иначе null)

Формат ответа — ТОЛЬКО JSON массив, без пояснений:
[{{"company_name":"Название из текста","description":"Что делает (из текста)","annual_revenue":"из текста или null","investment_round":"из текста или null","has_ru_competitor":true}}]

JSON:"""

        try:
            analyzer = AnalyzerService()
            response_text = await analyzer._call_llm(prompt, max_tokens=1000)
            
            # Parse JSON response — handle various LLM output formats
            response_text = response_text.strip()
            
            # Remove markdown code fences if present
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            
            # Try to find JSON array in response (LLM may add text around it)
            if not response_text.startswith("["):
                start = response_text.find("[")
                if start != -1:
                    end = response_text.rfind("]")
                    if end > start:
                        response_text = response_text[start:end+1]
            
            if not response_text or response_text == "[]":
                logger.info(f"LLM returned empty analogues for '{idea_name}'")
                return []
            
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
            
            logger.info(f"LLM extracted {len(analogues)} analogues for '{idea_name}'")
            return analogues
        except json.JSONDecodeError as e:
            logger.warning(f"LLM returned invalid JSON for analogues '{idea_name}': {e}, response: {response_text[:100]}")
            return []
        except Exception as e:
            logger.warning(f"LLM extraction of analogues failed for '{idea_name}': {e}")
            return []
