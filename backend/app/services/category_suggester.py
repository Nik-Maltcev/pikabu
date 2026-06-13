"""Category suggester service — recommends topics via LLM based on OKVED code or activity description."""

import json
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.schemas import CategorySuggestion
from app.services.topic_manager import TopicManager

logger = logging.getLogger(__name__)


class CategorySuggesterError(Exception):
    """Raised when category suggestion fails (LLM timeout, HTTP error, parse error)."""


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers if present."""
    text = text.strip()
    if text.startswith("```"):
        text = text[text.index("\n") + 1:]
        if text.endswith("```"):
            text = text[:-3].rstrip()
    return text


class CategorySuggesterService:
    """Suggests relevant categories via LLM based on user's OKVED code or description."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._topic_manager = TopicManager(session)
        # LLM config from settings (same pattern as AnalyzerService)
        if settings.llm_provider == "gemini":
            self._api_key = settings.gemini_api_key
            self._base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            self._model = settings.gemini_model
        elif settings.llm_provider == "glm":
            self._api_key = settings.glm_api_key
            self._base_url = "https://api.z.ai/api/paas/v4"
            self._model = settings.glm_model
        else:
            self._api_key = settings.llm_api_key
            self._base_url = settings.llm_base_url
            self._model = settings.llm_model

    async def suggest(self, query: str) -> list[CategorySuggestion]:
        """Suggest 2-5 categories based on OKVED code or activity description.

        Args:
            query: User input (OKVED code or activity description), 2-200 chars.

        Returns:
            List of CategorySuggestion (0-5 items).

        Raises:
            CategorySuggesterError: on LLM timeout, HTTP error, or persistent parse error.
        """
        topics = await self._topic_manager.fetch_topics(source="all")
        valid_ids = {t.id for t in topics}
        prompt = self._build_prompt(query, topics)

        # Try up to 2 times (1 retry on JSON parse error)
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                text = await self._call_llm(prompt)
                return self._parse_response(text, valid_ids)
            except json.JSONDecodeError as exc:
                last_error = exc
                logger.warning("Invalid JSON from LLM (attempt %d/2): %s", attempt + 1, exc)
                if attempt == 0:
                    continue
            except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                raise CategorySuggesterError(
                    "Сервис подбора временно недоступен. Выберите категории вручную."
                ) from exc

        raise CategorySuggesterError(
            "Не удалось разобрать ответ LLM. Выберите категории вручную."
        ) from last_error

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with 10s timeout."""
        # Force IPv4 for Gemini (Google blocks some IPv6 ranges)
        transport = (
            httpx.AsyncHTTPTransport(local_address="0.0.0.0")
            if settings.llm_provider == "gemini"
            else None
        )
        async with httpx.AsyncClient(timeout=10.0, transport=transport) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
            )
            response.raise_for_status()
            data = response.json()
            msg = data["choices"][0]["message"]
            content = msg.get("content") or ""
            if not content.strip():
                # Fallback: some models put output in reasoning_content
                reasoning = msg.get("reasoning_content") or ""
                if reasoning.strip():
                    content = reasoning
            return content

    def _build_prompt(self, query: str, topics) -> str:
        """Build LLM prompt with full topic list."""
        topics_formatted = "\n".join(f"{t.id} | {t.name}" for t in topics)
        return (
            f'Ты — эксперт по классификации бизнеса. Пользователь описал свою деятельность: "{query}".\n\n'
            f"Ниже — список доступных категорий для анализа (id | название):\n"
            f"{topics_formatted}\n\n"
            f"Подбери от 2 до 5 наиболее релевантных категорий. Для каждой укажи обоснование (до 100 символов).\n\n"
            f"Ответь строго в JSON:\n"
            f"[\n"
            f'  {{"topic_id": 123, "name": "Маркетинг", "reason": "..."}},\n'
            f"  ...\n"
            f"]\n\n"
            f"Правила:\n"
            f"- Используй ТОЛЬКО topic_id из списка выше\n"
            f"- Если ввод — ОКВЭД-код, определи вид деятельности и подбери категории\n"
            f"- Если не можешь подобрать — верни пустой массив []\n"
            f"- Не придумывай категории, которых нет в списке"
        )

    def _parse_response(self, text: str, valid_ids: set[int]) -> list[CategorySuggestion]:
        """Parse LLM JSON response, filter invalid topic_ids, limit to 5, truncate reason."""
        text = _strip_markdown_fences(text)
        items = json.loads(text)

        if not isinstance(items, list):
            raise json.JSONDecodeError("Expected a JSON array", text, 0)

        result: list[CategorySuggestion] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            topic_id = item.get("topic_id")
            if topic_id not in valid_ids:
                continue
            name = str(item.get("name", ""))
            reason = str(item.get("reason", ""))[:100]
            if not name:
                continue
            result.append(CategorySuggestion(topic_id=topic_id, name=name, reason=reason))
            if len(result) >= 5:
                break

        return result
