"""Analyzer service for processing chunks via Google Gemini API."""

import asyncio
import json
import logging

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

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
    """Raised when Gemini API is unavailable after all retry attempts."""


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
    """Build the full prompt for aggregating partial results."""
    data = []
    for r in results:
        data.append({
            "chunk_index": r.chunk_index,
            "topics_found": [t.model_dump() for t in r.topics_found],
            "user_problems": [p.model_dump() for p in r.user_problems],
            "active_discussions": [d.model_dump() for d in r.active_discussions],
        })
    data_json = json.dumps(data, ensure_ascii=False, indent=None)
    return AGGREGATION_PROMPT + data_json


def _parse_aggregation_result(response_text: str) -> dict:
    """Parse Gemini aggregation response into a report dict.

    Returns dict with keys: hot_topics, user_problems, trending_discussions.

    Raises:
        ValueError: If the response is not valid JSON or doesn't match the schema.
    """
    text = response_text.strip()
    if text.startswith("```"):
        first_newline = text.index("\n")
        text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3].rstrip()

    data = json.loads(text)

    hot_topics = [HotTopic(**t) for t in data.get("hot_topics", [])]
    user_problems = [UserProblem(**p) for p in data.get("user_problems", [])]
    trending = [TrendingDiscussion(**d) for d in data.get("trending_discussions", [])]

    return {
        "hot_topics": hot_topics,
        "user_problems": user_problems,
        "trending_discussions": trending,
    }


def _estimate_results_tokens(results: list[PartialResult]) -> int:
    """Estimate total tokens for a list of partial results when serialized."""
    prompt = _build_aggregation_prompt(results)
    return estimate_tokens(prompt)


def _build_chunk_prompt(chunk: Chunk) -> str:
    """Build the full prompt for analyzing a single chunk."""
    data_json = json.dumps(chunk.posts_data, ensure_ascii=False, indent=None)
    return CHUNK_ANALYSIS_PROMPT + data_json


def _parse_partial_result(chunk_index: int, response_text: str) -> PartialResult:
    """Parse Gemini response text into a PartialResult model.

    Strips markdown code fences if present, then parses JSON.

    Raises:
        ValueError: If the response is not valid JSON or doesn't match the schema.
    """
    text = response_text.strip()
    # Strip markdown code fences that Gemini sometimes wraps around JSON
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = text.index("\n")
        text = text[first_newline + 1 :]
        # Remove closing fence
        if text.endswith("```"):
            text = text[: -3].rstrip()

    data = json.loads(text)

    topics = [HotTopic(**t) for t in data.get("topics_found", [])]
    problems = [UserProblem(**p) for p in data.get("user_problems", [])]
    discussions = [TrendingDiscussion(**d) for d in data.get("active_discussions", [])]

    return PartialResult(
        chunk_index=chunk_index,
        topics_found=topics,
        user_problems=problems,
        active_discussions=discussions,
    )


class AnalyzerService:
    """Service for analyzing data chunks via Google Gemini API."""

    def __init__(self, api_key: str | None = None, max_retries: int | None = None):
        key = api_key or settings.gemini_api_key
        self.max_retries = max_retries if max_retries is not None else settings.gemini_max_retries
        genai.configure(api_key=key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    async def analyze_chunk(self, chunk: Chunk) -> PartialResult:
        """Send a chunk to Gemini API and return a PartialResult.

        Retries up to max_retries times with exponential backoff (2s, 4s, 8s, …).
        Retries on API errors and invalid JSON responses.

        Raises:
            AnalyzerError: If Gemini is unavailable after all retries.
        """
        prompt = _build_chunk_prompt(chunk)
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content, prompt
                )
                return _parse_partial_result(chunk.index, response.text)
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                last_error = exc
                logger.warning(
                    "Invalid JSON from Gemini (chunk %d, attempt %d/%d): %s",
                    chunk.index,
                    attempt + 1,
                    self.max_retries,
                    exc,
                )
            except (
                google_exceptions.GoogleAPIError,
                google_exceptions.RetryError,
                ConnectionError,
                TimeoutError,
            ) as exc:
                last_error = exc
                logger.warning(
                    "Gemini API error (chunk %d, attempt %d/%d): %s",
                    chunk.index,
                    attempt + 1,
                    self.max_retries,
                    exc,
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Unexpected error from Gemini (chunk %d, attempt %d/%d): %s",
                    chunk.index,
                    attempt + 1,
                    self.max_retries,
                    exc,
                )

            # Exponential backoff: 2s, 4s, 8s, …
            if attempt < self.max_retries - 1:
                delay = 2 ** (attempt + 1)
                logger.info("Retrying in %ds…", delay)
                await asyncio.sleep(delay)

        raise AnalyzerError(
            f"Gemini API unavailable after {self.max_retries} attempts "
            f"for chunk {chunk.index}: {last_error}"
        )

    async def aggregate_results(self, results: list[PartialResult]) -> dict:
        """Aggregate partial results into a final report via Gemini API.

        Sends all partial results to Gemini for merging/deduplication.
        Uses the same retry logic as analyze_chunk.

        Args:
            results: List of PartialResult from chunk analysis.

        Returns:
            Dict with keys: hot_topics, user_problems, trending_discussions.

        Raises:
            AnalyzerError: If Gemini is unavailable after all retries.
        """
        if not results:
            return {
                "hot_topics": [],
                "user_problems": [],
                "trending_discussions": [],
            }

        prompt = _build_aggregation_prompt(results)
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content, prompt
                )
                return _parse_aggregation_result(response.text)
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                last_error = exc
                logger.warning(
                    "Invalid JSON from Gemini during aggregation (attempt %d/%d): %s",
                    attempt + 1,
                    self.max_retries,
                    exc,
                )
            except (
                google_exceptions.GoogleAPIError,
                google_exceptions.RetryError,
                ConnectionError,
                TimeoutError,
            ) as exc:
                last_error = exc
                logger.warning(
                    "Gemini API error during aggregation (attempt %d/%d): %s",
                    attempt + 1,
                    self.max_retries,
                    exc,
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Unexpected error during aggregation (attempt %d/%d): %s",
                    attempt + 1,
                    self.max_retries,
                    exc,
                )

            if attempt < self.max_retries - 1:
                delay = 2 ** (attempt + 1)
                logger.info("Retrying aggregation in %ds…", delay)
                await asyncio.sleep(delay)

        raise AnalyzerError(
            f"Gemini API unavailable after {self.max_retries} attempts "
            f"during aggregation: {last_error}"
        )

    async def hierarchical_aggregate(
        self,
        results: list[PartialResult],
        max_group_size: int | None = None,
    ) -> dict:
        """Hierarchically aggregate partial results when they exceed context window.

        Splits results into groups that fit within the Gemini context window,
        aggregates each group into an intermediate result, then aggregates
        the intermediate results into the final report.

        Args:
            results: List of PartialResult from chunk analysis.
            max_group_size: Max tokens per group. Defaults to 80% of context window.

        Returns:
            Dict with keys: hot_topics, user_problems, trending_discussions.

        Raises:
            AnalyzerError: If Gemini is unavailable after all retries.
        """
        if not results:
            return {
                "hot_topics": [],
                "user_problems": [],
                "trending_discussions": [],
            }

        if max_group_size is None:
            max_group_size = int(settings.gemini_context_window * 0.8)

        # Check if all results fit in one call
        total_tokens = _estimate_results_tokens(results)
        if total_tokens <= max_group_size:
            return await self.aggregate_results(results)

        # Split results into groups that fit within the context window
        groups: list[list[PartialResult]] = []
        current_group: list[PartialResult] = []

        for result in results:
            candidate = current_group + [result]
            candidate_tokens = _estimate_results_tokens(candidate)

            if current_group and candidate_tokens > max_group_size:
                groups.append(current_group)
                current_group = [result]
            else:
                current_group = candidate

        if current_group:
            groups.append(current_group)

        # Aggregate each group into an intermediate result
        intermediate_results: list[PartialResult] = []
        for group_idx, group in enumerate(groups):
            report = await self.aggregate_results(group)
            intermediate = PartialResult(
                chunk_index=group_idx,
                topics_found=report["hot_topics"],
                user_problems=report["user_problems"],
                active_discussions=report["trending_discussions"],
            )
            intermediate_results.append(intermediate)

        # Check if intermediate results fit in one call, recurse if not
        intermediate_tokens = _estimate_results_tokens(intermediate_results)
        if intermediate_tokens > max_group_size:
            return await self.hierarchical_aggregate(
                intermediate_results, max_group_size
            )

        return await self.aggregate_results(intermediate_results)
