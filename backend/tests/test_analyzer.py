"""Tests for AnalyzerService — chunk analysis and aggregation with mocked Gemini API."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.models.schemas import Chunk, HotTopic, PartialResult, TrendingDiscussion, UserProblem
from app.services.analyzer import (
    AGGREGATION_PROMPT,
    AnalyzerError,
    AnalyzerService,
    _build_aggregation_prompt,
    _build_chunk_prompt,
    _parse_aggregation_result,
    _parse_partial_result,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_GEMINI_RESPONSE = json.dumps(
    {
        "topics_found": [
            {"name": "Тема 1", "description": "Описание", "mentions_count": 5}
        ],
        "user_problems": [
            {"description": "Проблема", "examples": ["пример 1"]}
        ],
        "active_discussions": [
            {
                "title": "Дискуссия",
                "description": "Описание",
                "post_url": "https://pikabu.ru/story/123",
                "activity_score": 0.8,
            }
        ],
    },
    ensure_ascii=False,
)


def _make_chunk(index: int = 0) -> Chunk:
    return Chunk(
        index=index,
        posts_data=[{"title": "Post", "body": "text", "url": "https://pikabu.ru/story/1"}],
        estimated_tokens=100,
    )


# ---------------------------------------------------------------------------
# _build_chunk_prompt
# ---------------------------------------------------------------------------


class TestBuildChunkPrompt:
    def test_contains_data(self):
        chunk = _make_chunk()
        prompt = _build_chunk_prompt(chunk)
        assert "Post" in prompt
        assert "pikabu.ru/story/1" in prompt

    def test_contains_instructions(self):
        prompt = _build_chunk_prompt(_make_chunk())
        assert "topics_found" in prompt
        assert "user_problems" in prompt
        assert "active_discussions" in prompt


# ---------------------------------------------------------------------------
# _parse_partial_result
# ---------------------------------------------------------------------------


class TestParsePartialResult:
    def test_valid_json(self):
        result = _parse_partial_result(0, VALID_GEMINI_RESPONSE)
        assert isinstance(result, PartialResult)
        assert result.chunk_index == 0
        assert len(result.topics_found) == 1
        assert result.topics_found[0].name == "Тема 1"
        assert len(result.user_problems) == 1
        assert len(result.active_discussions) == 1
        assert result.active_discussions[0].activity_score == 0.8

    def test_strips_markdown_fences(self):
        wrapped = "```json\n" + VALID_GEMINI_RESPONSE + "\n```"
        result = _parse_partial_result(1, wrapped)
        assert result.chunk_index == 1
        assert len(result.topics_found) == 1

    def test_empty_lists(self):
        data = json.dumps(
            {"topics_found": [], "user_problems": [], "active_discussions": []}
        )
        result = _parse_partial_result(2, data)
        assert result.topics_found == []
        assert result.user_problems == []
        assert result.active_discussions == []

    def test_invalid_json_raises(self):
        with pytest.raises((json.JSONDecodeError, ValueError)):
            _parse_partial_result(0, "not json at all")

    def test_missing_fields_defaults_to_empty(self):
        result = _parse_partial_result(0, "{}")
        assert result.topics_found == []
        assert result.user_problems == []
        assert result.active_discussions == []


# ---------------------------------------------------------------------------
# AnalyzerService.analyze_chunk — success
# ---------------------------------------------------------------------------


class TestAnalyzeChunkSuccess:
    @pytest.fixture(autouse=True)
    def _patch_genai(self):
        with patch("app.services.analyzer.genai") as mock_genai:
            self.mock_genai = mock_genai
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            self.mock_model = mock_model
            yield

    async def test_returns_partial_result(self):
        self.mock_model.generate_content.return_value = SimpleNamespace(
            text=VALID_GEMINI_RESPONSE
        )
        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.analyze_chunk(_make_chunk())
        assert isinstance(result, PartialResult)
        assert result.chunk_index == 0
        assert len(result.topics_found) == 1

    async def test_calls_model_with_prompt(self):
        self.mock_model.generate_content.return_value = SimpleNamespace(
            text=VALID_GEMINI_RESPONSE
        )
        svc = AnalyzerService(api_key="test-key", max_retries=3)
        await svc.analyze_chunk(_make_chunk())
        self.mock_model.generate_content.assert_called_once()
        prompt_arg = self.mock_model.generate_content.call_args[0][0]
        assert "topics_found" in prompt_arg


# ---------------------------------------------------------------------------
# AnalyzerService.analyze_chunk — retry on invalid JSON
# ---------------------------------------------------------------------------


class TestAnalyzeChunkRetryInvalidJson:
    @pytest.fixture(autouse=True)
    def _patch_genai(self):
        with patch("app.services.analyzer.genai") as mock_genai:
            self.mock_genai = mock_genai
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            self.mock_model = mock_model
            yield

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_retries_on_invalid_json_then_succeeds(self, mock_sleep):
        bad = SimpleNamespace(text="not json")
        good = SimpleNamespace(text=VALID_GEMINI_RESPONSE)
        self.mock_model.generate_content.side_effect = [bad, good]

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.analyze_chunk(_make_chunk())
        assert isinstance(result, PartialResult)
        assert self.mock_model.generate_content.call_count == 2
        # Backoff: first retry waits 2s
        mock_sleep.assert_called_once_with(2)

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_raises_after_all_retries_invalid_json(self, mock_sleep):
        self.mock_model.generate_content.return_value = SimpleNamespace(text="bad")

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        with pytest.raises(AnalyzerError, match="unavailable after 3 attempts"):
            await svc.analyze_chunk(_make_chunk())
        assert self.mock_model.generate_content.call_count == 3


# ---------------------------------------------------------------------------
# AnalyzerService.analyze_chunk — retry on API errors
# ---------------------------------------------------------------------------


class TestAnalyzeChunkRetryApiError:
    @pytest.fixture(autouse=True)
    def _patch_genai(self):
        with patch("app.services.analyzer.genai") as mock_genai:
            self.mock_genai = mock_genai
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            self.mock_model = mock_model
            yield

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_retries_on_connection_error_then_succeeds(self, mock_sleep):
        good = SimpleNamespace(text=VALID_GEMINI_RESPONSE)
        self.mock_model.generate_content.side_effect = [
            ConnectionError("network"),
            good,
        ]

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.analyze_chunk(_make_chunk())
        assert isinstance(result, PartialResult)
        mock_sleep.assert_called_once_with(2)

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_exponential_backoff_delays(self, mock_sleep):
        good = SimpleNamespace(text=VALID_GEMINI_RESPONSE)
        self.mock_model.generate_content.side_effect = [
            ConnectionError("err1"),
            TimeoutError("err2"),
            good,
        ]

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.analyze_chunk(_make_chunk())
        assert isinstance(result, PartialResult)
        # Delays: 2s after attempt 1, 4s after attempt 2
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_raises_analyzer_error_after_all_retries(self, mock_sleep):
        self.mock_model.generate_content.side_effect = ConnectionError("down")

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        with pytest.raises(AnalyzerError, match="unavailable after 3 attempts"):
            await svc.analyze_chunk(_make_chunk())
        assert self.mock_model.generate_content.call_count == 3
        # Backoff: 2s, 4s (no sleep after last attempt)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)


# ---------------------------------------------------------------------------
# Aggregation fixtures
# ---------------------------------------------------------------------------

VALID_AGGREGATION_RESPONSE = json.dumps(
    {
        "hot_topics": [
            {"name": "Объединённая тема", "description": "Описание", "mentions_count": 10}
        ],
        "user_problems": [
            {"description": "Общая проблема", "examples": ["пример 1", "пример 2"]}
        ],
        "trending_discussions": [
            {
                "title": "Топ дискуссия",
                "description": "Описание",
                "post_url": "https://pikabu.ru/story/123",
                "activity_score": 0.95,
            }
        ],
    },
    ensure_ascii=False,
)


def _make_partial_result(chunk_index: int = 0) -> PartialResult:
    return PartialResult(
        chunk_index=chunk_index,
        topics_found=[HotTopic(name="Тема", description="Описание", mentions_count=3)],
        user_problems=[UserProblem(description="Проблема", examples=["пример"])],
        active_discussions=[
            TrendingDiscussion(
                title="Дискуссия",
                description="Описание",
                post_url=f"https://pikabu.ru/story/{chunk_index}",
                activity_score=0.7,
            )
        ],
    )


# ---------------------------------------------------------------------------
# _build_aggregation_prompt
# ---------------------------------------------------------------------------


class TestBuildAggregationPrompt:
    def test_contains_partial_results_data(self):
        results = [_make_partial_result(0), _make_partial_result(1)]
        prompt = _build_aggregation_prompt(results)
        assert "Тема" in prompt
        assert "Проблема" in prompt
        assert "pikabu.ru/story/0" in prompt
        assert "pikabu.ru/story/1" in prompt

    def test_contains_instructions(self):
        prompt = _build_aggregation_prompt([_make_partial_result()])
        assert "hot_topics" in prompt
        assert "user_problems" in prompt
        assert "trending_discussions" in prompt

    def test_empty_results(self):
        prompt = _build_aggregation_prompt([])
        assert AGGREGATION_PROMPT in prompt
        assert "[]" in prompt


# ---------------------------------------------------------------------------
# _parse_aggregation_result
# ---------------------------------------------------------------------------


class TestParseAggregationResult:
    def test_valid_json(self):
        result = _parse_aggregation_result(VALID_AGGREGATION_RESPONSE)
        assert "hot_topics" in result
        assert "user_problems" in result
        assert "trending_discussions" in result
        assert len(result["hot_topics"]) == 1
        assert result["hot_topics"][0].name == "Объединённая тема"
        assert result["hot_topics"][0].mentions_count == 10
        assert len(result["user_problems"]) == 1
        assert len(result["trending_discussions"]) == 1
        assert result["trending_discussions"][0].activity_score == 0.95

    def test_strips_markdown_fences(self):
        wrapped = "```json\n" + VALID_AGGREGATION_RESPONSE + "\n```"
        result = _parse_aggregation_result(wrapped)
        assert len(result["hot_topics"]) == 1

    def test_empty_lists(self):
        data = json.dumps(
            {"hot_topics": [], "user_problems": [], "trending_discussions": []}
        )
        result = _parse_aggregation_result(data)
        assert result["hot_topics"] == []
        assert result["user_problems"] == []
        assert result["trending_discussions"] == []

    def test_invalid_json_raises(self):
        with pytest.raises((json.JSONDecodeError, ValueError)):
            _parse_aggregation_result("not json")

    def test_missing_fields_defaults_to_empty(self):
        result = _parse_aggregation_result("{}")
        assert result["hot_topics"] == []
        assert result["user_problems"] == []
        assert result["trending_discussions"] == []


# ---------------------------------------------------------------------------
# AnalyzerService.aggregate_results — success
# ---------------------------------------------------------------------------


class TestAggregateResultsSuccess:
    @pytest.fixture(autouse=True)
    def _patch_genai(self):
        with patch("app.services.analyzer.genai") as mock_genai:
            self.mock_genai = mock_genai
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            self.mock_model = mock_model
            yield

    async def test_returns_report_dict(self):
        self.mock_model.generate_content.return_value = SimpleNamespace(
            text=VALID_AGGREGATION_RESPONSE
        )
        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.aggregate_results([_make_partial_result(0), _make_partial_result(1)])
        assert "hot_topics" in result
        assert "user_problems" in result
        assert "trending_discussions" in result
        assert len(result["hot_topics"]) == 1

    async def test_empty_results_returns_empty_report(self):
        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.aggregate_results([])
        assert result == {
            "hot_topics": [],
            "user_problems": [],
            "trending_discussions": [],
        }
        # Should not call Gemini for empty input
        self.mock_model.generate_content.assert_not_called()

    async def test_calls_model_with_aggregation_prompt(self):
        self.mock_model.generate_content.return_value = SimpleNamespace(
            text=VALID_AGGREGATION_RESPONSE
        )
        svc = AnalyzerService(api_key="test-key", max_retries=3)
        await svc.aggregate_results([_make_partial_result()])
        self.mock_model.generate_content.assert_called_once()
        prompt_arg = self.mock_model.generate_content.call_args[0][0]
        assert "hot_topics" in prompt_arg
        assert "merge" in prompt_arg.lower() or "Merge" in prompt_arg


# ---------------------------------------------------------------------------
# AnalyzerService.aggregate_results — retry logic
# ---------------------------------------------------------------------------


class TestAggregateResultsRetry:
    @pytest.fixture(autouse=True)
    def _patch_genai(self):
        with patch("app.services.analyzer.genai") as mock_genai:
            self.mock_genai = mock_genai
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            self.mock_model = mock_model
            yield

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_retries_on_invalid_json_then_succeeds(self, mock_sleep):
        bad = SimpleNamespace(text="not json")
        good = SimpleNamespace(text=VALID_AGGREGATION_RESPONSE)
        self.mock_model.generate_content.side_effect = [bad, good]

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.aggregate_results([_make_partial_result()])
        assert "hot_topics" in result
        assert self.mock_model.generate_content.call_count == 2
        mock_sleep.assert_called_once_with(2)

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_retries_on_connection_error(self, mock_sleep):
        good = SimpleNamespace(text=VALID_AGGREGATION_RESPONSE)
        self.mock_model.generate_content.side_effect = [ConnectionError("net"), good]

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.aggregate_results([_make_partial_result()])
        assert "hot_topics" in result
        mock_sleep.assert_called_once_with(2)

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_raises_after_all_retries(self, mock_sleep):
        self.mock_model.generate_content.side_effect = ConnectionError("down")

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        with pytest.raises(AnalyzerError, match="during aggregation"):
            await svc.aggregate_results([_make_partial_result()])
        assert self.mock_model.generate_content.call_count == 3

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_exponential_backoff(self, mock_sleep):
        good = SimpleNamespace(text=VALID_AGGREGATION_RESPONSE)
        self.mock_model.generate_content.side_effect = [
            ConnectionError("e1"),
            TimeoutError("e2"),
            good,
        ]

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.aggregate_results([_make_partial_result()])
        assert "hot_topics" in result
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)


# ---------------------------------------------------------------------------
# AnalyzerService.hierarchical_aggregate
# ---------------------------------------------------------------------------


class TestHierarchicalAggregate:
    @pytest.fixture(autouse=True)
    def _patch_genai(self):
        with patch("app.services.analyzer.genai") as mock_genai:
            self.mock_genai = mock_genai
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            self.mock_model = mock_model
            yield

    async def test_empty_results(self):
        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.hierarchical_aggregate([])
        assert result == {
            "hot_topics": [],
            "user_problems": [],
            "trending_discussions": [],
        }

    async def test_small_input_delegates_to_aggregate(self):
        """When results fit in one call, should just call aggregate_results."""
        self.mock_model.generate_content.return_value = SimpleNamespace(
            text=VALID_AGGREGATION_RESPONSE
        )
        svc = AnalyzerService(api_key="test-key", max_retries=3)
        results = [_make_partial_result(0)]
        # Use a large max_group_size so everything fits
        result = await svc.hierarchical_aggregate(results, max_group_size=100_000)
        assert "hot_topics" in result
        # Only one call to Gemini (the single aggregate)
        assert self.mock_model.generate_content.call_count == 1

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_splits_into_groups_when_exceeding_limit(self, mock_sleep):
        """When results exceed max_group_size, should split into groups."""
        self.mock_model.generate_content.return_value = SimpleNamespace(
            text=VALID_AGGREGATION_RESPONSE
        )
        svc = AnalyzerService(api_key="test-key", max_retries=3)
        # Create many partial results
        results = [_make_partial_result(i) for i in range(10)]
        # Estimate tokens for a single result to pick a limit that forces
        # splitting into multiple groups but still fits individual results.
        from app.services.analyzer import _estimate_results_tokens
        single_tokens = _estimate_results_tokens([results[0]])
        # Allow ~2 results per group
        max_group = single_tokens + (single_tokens // 2)
        result = await svc.hierarchical_aggregate(results, max_group_size=max_group)
        assert "hot_topics" in result
        # Should have made multiple calls (groups + final aggregation)
        assert self.mock_model.generate_content.call_count > 1

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_propagates_analyzer_error(self, mock_sleep):
        """If Gemini fails during hierarchical aggregation, AnalyzerError is raised."""
        self.mock_model.generate_content.side_effect = ConnectionError("down")
        svc = AnalyzerService(api_key="test-key", max_retries=3)
        results = [_make_partial_result(i) for i in range(5)]
        from app.services.analyzer import _estimate_results_tokens
        single_tokens = _estimate_results_tokens([results[0]])
        max_group = single_tokens + (single_tokens // 2)
        with pytest.raises(AnalyzerError):
            await svc.hierarchical_aggregate(results, max_group_size=max_group)


# ---------------------------------------------------------------------------
# Error handling: partial results preserved on aggregation failure
# ---------------------------------------------------------------------------


class TestAggregationErrorPreservesPartialResults:
    @pytest.fixture(autouse=True)
    def _patch_genai(self):
        with patch("app.services.analyzer.genai") as mock_genai:
            self.mock_genai = mock_genai
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            self.mock_model = mock_model
            yield

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_partial_results_intact_after_aggregation_failure(self, mock_sleep):
        """Partial results should remain accessible even when aggregation fails."""
        self.mock_model.generate_content.side_effect = ConnectionError("down")
        svc = AnalyzerService(api_key="test-key", max_retries=3)

        partial_results = [_make_partial_result(0), _make_partial_result(1)]

        with pytest.raises(AnalyzerError):
            await svc.aggregate_results(partial_results)

        # Partial results are not mutated — caller can still save them
        assert len(partial_results) == 2
        assert partial_results[0].chunk_index == 0
        assert partial_results[1].chunk_index == 1
        assert len(partial_results[0].topics_found) == 1
        assert len(partial_results[1].topics_found) == 1
