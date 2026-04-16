"""Analyzer service for processing chunks via LLM (Qwen via OpenAI-compatible API)."""

import asyncio
import json
import logging

import httpx

from app.config import settings
from app.models.schemas import (
    Chunk,
    HotTopic,
    PartialResult,
    TrendingDiscussion,
    UserProblem,
)
from app.services.chunker import estimate_tokens

logger = logging.getLogger(__name__)


class AnalyzerError(Exception):
    """Raised when LLM API is unavailable after all retry attempts."""


CHUNK_ANALYSIS_PROMPT = """\
You are an expert content analyst for the Russian social platform Pikabu.

Analyze the following chunk of posts and comments data. Identify:

1. **Frequently discussed topics** — recurring themes or subjects people talk about.
   For each topic provide: name, short description, and approximate mentions_count in this chunk.

2. **User problems / pain points** — issues, complaints, or frustrations users express.
   For each problem provide: description and a list of example quotes (short, 1-2 sentences each).

3. **Active discussions** — posts that generated significant engagement or debate.
   For each discussion provide: title, short description, post_url from the data, and activity_score (0.0 to 1.0).

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
    text = response_text.strip()
    if text.startswith("```"):
        text = text[text.index("\n") + 1:]
        if text.endswith("```"):
            text = text[:-3].rstrip()
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
    text = response_text.strip()
    if text.startswith("```"):
        text = text[text.index("\n") + 1:]
        if text.endswith("```"):
            text = text[:-3].rstrip()
    data = json.loads(text)
    return PartialResult(
        chunk_index=chunk_index,
        topics_found=[HotTopic(**t) for t in data.get("topics_found", [])],
        user_problems=[UserProblem(**p) for p in data.get("user_problems", [])],
        active_discussions=[TrendingDiscussion(**d) for d in data.get("active_discussions", [])],
    )


class AnalyzerService:
    """Service for analyzing data chunks via LLM (OpenAI-compatible API)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_retries: int | None = None,
    ):
        self.api_key = api_key or settings.llm_api_key
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.llm_model
        self.max_retries = max_retries if max_retries is not None else settings.llm_max_retries

    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM API and return the response text."""
        logger.info("LLM request: model=%s, prompt_len=%d chars, ~%d tokens", self.model, len(prompt), len(prompt) // 4)
        async with httpx.AsyncClient(timeout=300.0) as client:
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
                    "max_tokens": 8192,
                },
            )
            if response.status_code != 200:
                logger.error("LLM response %d: %s", response.status_code, response.text[:500])
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def analyze_chunk(self, chunk: Chunk) -> PartialResult:
        """Send a chunk to LLM and return a PartialResult."""
        prompt = _build_chunk_prompt(chunk)
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                text = await self._call_llm(prompt)
                return _parse_partial_result(chunk.index, text)
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                last_error = exc
                logger.warning("Invalid JSON from LLM (chunk %d, attempt %d/%d): %s", chunk.index, attempt + 1, self.max_retries, exc)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.warning("LLM API HTTP error (chunk %d, attempt %d/%d): %s", chunk.index, attempt + 1, self.max_retries, exc)
            except Exception as exc:
                last_error = exc
                logger.warning("LLM error (chunk %d, attempt %d/%d): %s", chunk.index, attempt + 1, self.max_retries, exc)

            if attempt < self.max_retries - 1:
                delay = 2 ** (attempt + 1)
                await asyncio.sleep(delay)

        raise AnalyzerError(f"LLM unavailable after {self.max_retries} attempts for chunk {chunk.index}: {last_error}")

    async def aggregate_results(self, results: list[PartialResult]) -> dict:
        """Aggregate partial results into a final report."""
        if not results:
            return {"hot_topics": [], "user_problems": [], "trending_discussions": []}

        prompt = _build_aggregation_prompt(results)
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                text = await self._call_llm(prompt)
                return _parse_aggregation_result(text)
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                last_error = exc
                logger.warning("Invalid JSON during aggregation (attempt %d/%d): %s", attempt + 1, self.max_retries, exc)
            except Exception as exc:
                last_error = exc
                logger.warning("LLM error during aggregation (attempt %d/%d): %s", attempt + 1, self.max_retries, exc)

            if attempt < self.max_retries - 1:
                delay = 2 ** (attempt + 1)
                await asyncio.sleep(delay)

        raise AnalyzerError(f"LLM unavailable after {self.max_retries} attempts during aggregation: {last_error}")

    async def hierarchical_aggregate(self, results: list[PartialResult], max_group_size: int | None = None) -> dict:
        """Hierarchically aggregate when results exceed context window."""
        if not results:
            return {"hot_topics": [], "user_problems": [], "trending_discussions": []}

        if max_group_size is None:
            max_group_size = int(settings.llm_context_window * 0.8)

        total_tokens = _estimate_results_tokens(results)
        if total_tokens <= max_group_size:
            return await self.aggregate_results(results)

        groups: list[list[PartialResult]] = []
        current_group: list[PartialResult] = []

        for result in results:
            candidate = current_group + [result]
            if current_group and _estimate_results_tokens(candidate) > max_group_size:
                groups.append(current_group)
                current_group = [result]
            else:
                current_group = candidate

        if current_group:
            groups.append(current_group)

        intermediate_results: list[PartialResult] = []
        for group_idx, group in enumerate(groups):
            report = await self.aggregate_results(group)
            intermediate_results.append(PartialResult(
                chunk_index=group_idx,
                topics_found=report["hot_topics"],
                user_problems=report["user_problems"],
                active_discussions=report["trending_discussions"],
            ))

        if _estimate_results_tokens(intermediate_results) > max_group_size:
            return await self.hierarchical_aggregate(intermediate_results, max_group_size)

        return await self.aggregate_results(intermediate_results)
