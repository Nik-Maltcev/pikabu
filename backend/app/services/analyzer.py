"""Analyzer service for processing chunks via LLM (Qwen via OpenAI-compatible API)."""

import asyncio
import json
import logging

import httpx

from app.config import settings
from app.models.schemas import (
    BusinessIdea,
    Chunk,
    HotTopic,
    JTBDAnalysis,
    KeyPain,
    MarketTrend,
    NichePartialResult,
    NicheReport,
    PartialResult,
    TrendingDiscussion,
    UserProblem,
)
from app.services.chunker import estimate_tokens

logger = logging.getLogger(__name__)


class AnalyzerError(Exception):
    """Raised when LLM API is unavailable after all retry attempts."""


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers if present."""
    text = text.strip()
    if text.startswith("```"):
        text = text[text.index("\n") + 1:]
        if text.endswith("```"):
            text = text[:-3].rstrip()
    return text


def _repair_truncated_json(text: str) -> str:
    """Attempt to repair JSON truncated by max_tokens.

    Strategy: close any open strings, arrays, and objects from the end.
    """
    # Try parsing as-is first
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # Truncated JSON repair: strip trailing incomplete value, close brackets
    repaired = text.rstrip()
    # Remove trailing comma or incomplete key-value
    while repaired and repaired[-1] in (',', ':', '"', ' ', '\n', '\r', '\t'):
        if repaired[-1] == '"':
            # Close the unterminated string
            repaired += '"'
            break
        repaired = repaired[:-1]

    # Count open brackets and close them
    open_braces = repaired.count('{') - repaired.count('}')
    open_brackets = repaired.count('[') - repaired.count(']')

    # Remove trailing comma before closing
    repaired = repaired.rstrip().rstrip(',')

    repaired += ']' * max(open_brackets, 0)
    repaired += '}' * max(open_braces, 0)

    logger.warning("Repaired truncated JSON: added %d ] and %d }", max(open_brackets, 0), max(open_braces, 0))
    return repaired


CHUNK_ANALYSIS_PROMPT = """\
You are an expert content analyst for the Russian social platform Pikabu.

Analyze the following chunk of posts and comments data. Identify:

1. **Frequently discussed topics** — recurring themes or subjects people talk about.
   For each topic provide: name, short description, and approximate mentions_count in this chunk.

2. **User problems / pain points** — issues, complaints, or frustrations users express.
   For each problem provide: description and a list of example quotes (short, 1-2 sentences each).

3. **Active discussions** — posts that generated significant engagement or debate.
   For each discussion provide: title, short description, post_url from the data, and activity_score (0.0 to 1.0).

Ограничения по объёму ответа:
- topics_found: не более 10 элементов, только наиболее значимые
- user_problems: не более 5 элементов
- examples в каждом user_problems: не более 3 цитат
- active_discussions: не более 5 элементов
Возвращай только наиболее значимые результаты.

Return your answer as a single JSON object with exactly this structure (no markdown, no extra text):
{
  "topics_found": [
    {"name": "...", "description": "...", "mentions_count": 0}
  ],
  "user_problems": [
    {"description": "...", "examples": ["...", "..."]}
  ],
  "active_discussions": [
    {"title": "...", "description": "...", "post_url": "...", "activity_score": 0.0}
  ]
}

Data to analyze:
"""


AGGREGATION_PROMPT = """\
You are an expert content analyst for the Russian social platform Pikabu.

You are given partial analysis results from multiple data chunks. Your task is to \
merge and deduplicate them into a single consolidated report.

Instructions:
1. **hot_topics** — Merge topics with the same or very similar names. Sum their \
mentions_count. Keep the best description. Rank by total mentions descending.
2. **user_problems** — Consolidate similar problems into one entry. Merge example \
quotes, removing exact duplicates. Keep the most descriptive problem description.
3. **trending_discussions** — Deduplicate by post_url. Keep the entry with the \
highest activity_score. Sort by activity_score descending.

Ограничения по объёму ответа:
- hot_topics: не более 15 элементов
- user_problems: не более 10 элементов
- trending_discussions: не более 10 элементов

Return your answer as a single JSON object with exactly this structure (no markdown, no extra text):
{
  "hot_topics": [
    {"name": "...", "description": "...", "mentions_count": 0}
  ],
  "user_problems": [
    {"description": "...", "examples": ["...", "..."]}
  ],
  "trending_discussions": [
    {"title": "...", "description": "...", "post_url": "...", "activity_score": 0.0}
  ]
}

Partial results to aggregate:
"""


def _build_aggregation_prompt(results: list[PartialResult]) -> str:
    data = []
    for r in results:
        data.append({
            "chunk_index": r.chunk_index,
            "topics_found": [t.model_dump() for t in r.topics_found],
            "user_problems": [p.model_dump() for p in r.user_problems],
            "active_discussions": [d.model_dump() for d in r.active_discussions],
        })
    return AGGREGATION_PROMPT + json.dumps(data, ensure_ascii=False)


def _parse_aggregation_result(response_text: str) -> dict:
    text = _strip_markdown_fences(response_text)
    text = _repair_truncated_json(text)
    data = json.loads(text)
    return {
        "hot_topics": [HotTopic(**t) for t in data.get("hot_topics", [])],
        "user_problems": [UserProblem(**p) for p in data.get("user_problems", [])],
        "trending_discussions": [TrendingDiscussion(**d) for d in data.get("trending_discussions", [])],
    }


def _estimate_results_tokens(results: list[PartialResult]) -> int:
    return estimate_tokens(_build_aggregation_prompt(results))


def _build_chunk_prompt(chunk: Chunk) -> str:
    return CHUNK_ANALYSIS_PROMPT + json.dumps(chunk.posts_data, ensure_ascii=False)


def _parse_partial_result(chunk_index: int, response_text: str) -> PartialResult:
    text = _strip_markdown_fences(response_text)
    text = _repair_truncated_json(text)
    data = json.loads(text)
    return PartialResult(
        chunk_index=chunk_index,
        topics_found=[HotTopic(**t) for t in data.get("topics_found", [])],
        user_problems=[UserProblem(**p) for p in data.get("user_problems", [])],
        active_discussions=[TrendingDiscussion(**d) for d in data.get("active_discussions", [])],
    )


# ---------------------------------------------------------------------------
# Niche search prompts and helpers
# ---------------------------------------------------------------------------

NICHE_CHUNK_PROMPT = """\
Ты — ИИ-стратег по поиску продуктовых ниш и стартап-идей. Твоя задача — \
анализировать «сырые» боли пользователей с форумов (Пикабу, VC, Хабр) и \
превращать их в конкретные бизнес-возможности. Ты не даёшь поверхностных \
ответов, а копаешь вглубь: «Какую работу должен выполнить продукт?» (JTBD).

Проанализируй следующий блок постов и комментариев. Извлеки:

1. **Ключевые боли** — реальные жалобы, проблемы и фрустрации пользователей.
   Для каждой боли укажи:
   - description: формулировка боли от первого лица (как «плач пользователя»)
   - frequency: градация частоты ("Массово", "Часто", "Периодически", "Редко, но метко")
   - emotional_charge: эмоциональный заряд ("Высокий" или "Средний")
   - examples: до 3 коротких цитат из данных

2. **JTBD-анализ** — для 3 самых перспективных болей разложи по структуре:
   - pain_description: краткое описание боли
   - situational: в какой момент возникает боль (контекст)
   - functional: что практическое хочет получить человек
   - emotional: как он хочет себя чувствовать (спокойствие, контроль, превосходство)
   - current_solution: что используют сейчас и почему это бесит

Ограничения по объёму ответа:
- key_pains: не более 10 элементов
- jtbd_analyses: не более 3 элементов
- examples в каждом key_pains: не более 3 цитат
Возвращай только наиболее значимые результаты.

Верни ответ как единый JSON-объект строго по этой структуре (без markdown, без лишнего текста):
{
  "key_pains": [
    {"description": "...", "frequency": "...", "emotional_charge": "...", "examples": ["..."]}
  ],
  "jtbd_analyses": [
    {"pain_description": "...", "situational": "...", "functional": "...", "emotional": "...", "current_solution": "..."}
  ]
}

Данные для анализа:
"""

NICHE_AGGREGATION_PROMPT = """\
Ты — ИИ-стратег по поиску продуктовых ниш и стартап-идей.

Тебе даны частичные результаты анализа болей пользователей из нескольких блоков данных. \
Твоя задача — объединить их и сгенерировать полный структурированный отчёт.

Инструкции:

1. **ТОП-5 Ключевых болей** — объедини похожие боли, выбери 5 самых частых и острых. \
Для каждой укажи description (от первого лица), frequency, emotional_charge, examples (до 3).

2. **JTBD-Анализ** — выбери 3 самые перспективные боли и разложи по структуре: \
pain_description, situational (контекст), functional (функциональная задача), \
emotional (эмоциональная задача), current_solution (текущее решение и почему бесит).

3. **Бизнес-идеи** — предложи 5 конкретных идей продуктов/услуг/сервисов. \
Для каждой: name (кликбейт-нейминг), description (суть в 2 предложениях), \
mvp_plan (что сделать за 2 выходных без программирования для проверки спроса).

4. **Тренды и рыночный контекст** — укажи 2-3 технологических или социальных тренда, \
которые усиливают эти проблемы. Для каждого: name, description, monetization_hint.

Ограничения по объёму ответа:
- key_pains: не более 5 элементов
- jtbd_analyses: не более 3 элементов
- business_ideas: не более 5 элементов
- market_trends: не более 3 элементов

Верни ответ как единый JSON-объект строго по этой структуре (без markdown, без лишнего текста):
{
  "key_pains": [
    {"description": "...", "frequency": "...", "emotional_charge": "...", "examples": ["..."]}
  ],
  "jtbd_analyses": [
    {"pain_description": "...", "situational": "...", "functional": "...", "emotional": "...", "current_solution": "..."}
  ],
  "business_ideas": [
    {"name": "...", "description": "...", "mvp_plan": "..."}
  ],
  "market_trends": [
    {"name": "...", "description": "...", "monetization_hint": "..."}
  ]
}

Частичные результаты для агрегации:
"""


def _build_niche_chunk_prompt(chunk: Chunk) -> str:
    return NICHE_CHUNK_PROMPT + json.dumps(chunk.posts_data, ensure_ascii=False)


def _parse_niche_partial_result(chunk_index: int, response_text: str) -> NichePartialResult:
    text = _strip_markdown_fences(response_text)
    text = _repair_truncated_json(text)
    data = json.loads(text)
    return NichePartialResult(
        chunk_index=chunk_index,
        key_pains=[KeyPain(**p) for p in data.get("key_pains", [])],
        jtbd_analyses=[JTBDAnalysis(**j) for j in data.get("jtbd_analyses", [])],
    )


def _build_niche_aggregation_prompt(results: list[NichePartialResult]) -> str:
    data = []
    for r in results:
        data.append({
            "chunk_index": r.chunk_index,
            "key_pains": [p.model_dump() for p in r.key_pains],
            "jtbd_analyses": [j.model_dump() for j in r.jtbd_analyses],
        })
    return NICHE_AGGREGATION_PROMPT + json.dumps(data, ensure_ascii=False)


def _parse_niche_aggregation_result(response_text: str) -> dict:
    text = _strip_markdown_fences(response_text)
    text = _repair_truncated_json(text)
    data = json.loads(text)
    return {
        "key_pains": [KeyPain(**p) for p in data.get("key_pains", [])],
        "jtbd_analyses": [JTBDAnalysis(**j) for j in data.get("jtbd_analyses", [])],
        "business_ideas": [BusinessIdea(**b) for b in data.get("business_ideas", [])],
        "market_trends": [MarketTrend(**m) for m in data.get("market_trends", [])],
    }


def _estimate_niche_results_tokens(results: list[NichePartialResult]) -> int:
    return estimate_tokens(_build_niche_aggregation_prompt(results))


class AnalyzerService:
    """Service for analyzing data chunks via LLM (DeepSeek, Gemini, or GLM)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_retries: int | None = None,
        provider: str | None = None,
    ):
        self.provider = provider or settings.llm_provider
        self.max_retries = max_retries if max_retries is not None else settings.llm_max_retries

        if self.provider == "gemini":
            self.api_key = api_key or settings.gemini_api_key
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            self.model = model or settings.gemini_model
        elif self.provider == "glm":
            self.api_key = api_key or settings.glm_api_key
            self.base_url = "https://api.z.ai/api/paas/v4"
            self.model = model or settings.glm_model
        else:
            self.api_key = api_key or settings.llm_api_key
            self.base_url = base_url or settings.llm_base_url
            self.model = model or settings.llm_model

    async def _call_llm(self, prompt: str, max_tokens: int | None = None) -> str:
        """Call the LLM API and return the response text.

        Args:
            prompt: The prompt to send to the LLM.
            max_tokens: Maximum tokens for the response. Falls back to
                ``settings.llm_max_tokens_chunk`` when not provided.
        """
        if max_tokens is None:
            max_tokens = settings.llm_max_tokens_chunk

        logger.info("LLM request: provider=%s, model=%s, prompt_len=%d chars, ~%d tokens, max_tokens=%d",
                     self.provider, self.model, len(prompt), len(prompt) // 4, max_tokens)

        # Force IPv4 for Gemini (Google blocks some IPv6 ranges)
        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0") if self.provider == "gemini" else None
        async with httpx.AsyncClient(timeout=300.0, transport=transport) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": max_tokens,
                    "reasoning_effort": "none",
                },
            )
            if response.status_code != 200:
                logger.error("LLM response %d: %s", response.status_code, response.text[:500])
            response.raise_for_status()
            data = response.json()
            msg = data["choices"][0]["message"]
            content = msg.get("content") or ""
            if not content.strip():
                # Fallback: some models put output in reasoning_content
                reasoning = msg.get("reasoning_content") or ""
                if reasoning.strip():
                    logger.warning("LLM content empty, using reasoning_content (%d chars)", len(reasoning))
                    content = reasoning
            if not content or not content.strip():
                logger.warning("LLM returned empty content. Full response: %s", json.dumps(data)[:1000])
                raise ValueError("LLM returned empty response content")
            logger.info("LLM response: %d chars", len(content))
            return content

    async def analyze_chunk(self, chunk: Chunk, *, analysis_mode: str = "topic_analysis") -> PartialResult | NichePartialResult:
        """Send a chunk to LLM and return a PartialResult or NichePartialResult."""
        if analysis_mode == "niche_search":
            prompt = _build_niche_chunk_prompt(chunk)
        else:
            prompt = _build_chunk_prompt(chunk)
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                text = await self._call_llm(prompt, max_tokens=settings.llm_max_tokens_chunk)
                if analysis_mode == "niche_search":
                    return _parse_niche_partial_result(chunk.index, text)
                return _parse_partial_result(chunk.index, text)
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                last_error = exc
                logger.warning("Invalid JSON from LLM (chunk %d, attempt %d/%d): %s", chunk.index, attempt + 1, self.max_retries, exc)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code == 429:
                    delay = 20 * (attempt + 1)
                    logger.warning("LLM 429 rate limit (chunk %d, attempt %d/%d), waiting %ds", chunk.index, attempt + 1, self.max_retries, delay)
                    await asyncio.sleep(delay)
                    continue
                logger.warning("LLM API HTTP error (chunk %d, attempt %d/%d): %s", chunk.index, attempt + 1, self.max_retries, exc)
            except Exception as exc:
                last_error = exc
                logger.warning("LLM error (chunk %d, attempt %d/%d): %s", chunk.index, attempt + 1, self.max_retries, exc)

            if attempt < self.max_retries - 1:
                delay = 2 ** (attempt + 1)
                await asyncio.sleep(delay)

        raise AnalyzerError(f"LLM unavailable after {self.max_retries} attempts for chunk {chunk.index}: {last_error}")

    async def aggregate_results(self, results, *, analysis_mode: str = "topic_analysis") -> dict:
        """Aggregate partial results into a final report."""
        if not results:
            if analysis_mode == "niche_search":
                return {"key_pains": [], "jtbd_analyses": [], "business_ideas": [], "market_trends": []}
            return {"hot_topics": [], "user_problems": [], "trending_discussions": []}

        if analysis_mode == "niche_search":
            prompt = _build_niche_aggregation_prompt(results)
        else:
            prompt = _build_aggregation_prompt(results)
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                text = await self._call_llm(prompt, max_tokens=settings.llm_max_tokens_aggregation)
                if analysis_mode == "niche_search":
                    return _parse_niche_aggregation_result(text)
                return _parse_aggregation_result(text)
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                last_error = exc
                logger.warning("Invalid JSON during aggregation (attempt %d/%d): %s", attempt + 1, self.max_retries, exc)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code == 429:
                    delay = 20 * (attempt + 1)
                    logger.warning("LLM 429 rate limit during aggregation (attempt %d/%d), waiting %ds", attempt + 1, self.max_retries, delay)
                    await asyncio.sleep(delay)
                    continue
                logger.warning("LLM error during aggregation (attempt %d/%d): %s", attempt + 1, self.max_retries, exc)
            except Exception as exc:
                last_error = exc
                logger.warning("LLM error during aggregation (attempt %d/%d): %s", attempt + 1, self.max_retries, exc)

            if attempt < self.max_retries - 1:
                delay = 2 ** (attempt + 1)
                await asyncio.sleep(delay)

        raise AnalyzerError(f"LLM unavailable after {self.max_retries} attempts during aggregation: {last_error}")

    async def hierarchical_aggregate(self, results, *, analysis_mode: str = "topic_analysis", max_group_size: int | None = None) -> dict:
        """Hierarchically aggregate when results exceed context window."""
        if not results:
            if analysis_mode == "niche_search":
                return {"key_pains": [], "jtbd_analyses": [], "business_ideas": [], "market_trends": []}
            return {"hot_topics": [], "user_problems": [], "trending_discussions": []}

        if max_group_size is None:
            max_group_size = settings.llm_chunk_size

        if analysis_mode == "niche_search":
            total_tokens = _estimate_niche_results_tokens(results)
        else:
            total_tokens = _estimate_results_tokens(results)
        if total_tokens <= max_group_size:
            return await self.aggregate_results(results, analysis_mode=analysis_mode)

        groups = []
        current_group = []

        for result in results:
            candidate = current_group + [result]
            if analysis_mode == "niche_search":
                est = _estimate_niche_results_tokens(candidate)
            else:
                est = _estimate_results_tokens(candidate)
            if current_group and est > max_group_size:
                groups.append(current_group)
                current_group = [result]
            else:
                current_group = candidate

        if current_group:
            groups.append(current_group)

        intermediate_results = []
        for group_idx, group in enumerate(groups):
            report = await self.aggregate_results(group, analysis_mode=analysis_mode)
            if analysis_mode == "niche_search":
                intermediate_results.append(NichePartialResult(
                    chunk_index=group_idx,
                    key_pains=report["key_pains"],
                    jtbd_analyses=report["jtbd_analyses"],
                ))
            else:
                intermediate_results.append(PartialResult(
                    chunk_index=group_idx,
                    topics_found=report["hot_topics"],
                    user_problems=report["user_problems"],
                    active_discussions=report["trending_discussions"],
                ))

        if analysis_mode == "niche_search":
            if _estimate_niche_results_tokens(intermediate_results) > max_group_size:
                return await self.hierarchical_aggregate(intermediate_results, analysis_mode=analysis_mode, max_group_size=max_group_size)
        else:
            if _estimate_results_tokens(intermediate_results) > max_group_size:
                return await self.hierarchical_aggregate(intermediate_results, analysis_mode=analysis_mode, max_group_size=max_group_size)

        return await self.aggregate_results(intermediate_results, analysis_mode=analysis_mode)
