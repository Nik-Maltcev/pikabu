"""Tests for AnalyzerService — chunk analysis and aggregation with mocked httpx API."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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

VALID_CHUNK_RESPONSE = json.dumps(
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


def _make_httpx_response(content: str, status_code: int = 200) -> httpx.Response:
    """Build a fake httpx.Response with the given JSON content."""
    body = json.dumps({
        "choices": [{"message": {"content": content}}]
    })
    return httpx.Response(
        status_code=status_code,
        request=httpx.Request("POST", "https://api.deepseek.com/v1/chat/completions"),
        content=body.encode(),
    )


def _make_httpx_error_response(status_code: int, text: str = "error") -> httpx.Response:
    """Build a fake httpx.Response that will raise on raise_for_status()."""
    return httpx.Response(
        status_code=status_code,
        request=httpx.Request("POST", "https://api.deepseek.com/v1/chat/completions"),
        content=text.encode(),
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
        result = _parse_partial_result(0, VALID_CHUNK_RESPONSE)
        assert isinstance(result, PartialResult)
        assert result.chunk_index == 0
        assert len(result.topics_found) == 1
        assert result.topics_found[0].name == "Тема 1"
        assert len(result.user_problems) == 1
        assert len(result.active_discussions) == 1
        assert result.active_discussions[0].activity_score == 0.8

    def test_strips_markdown_fences(self):
        wrapped = "```json\n" + VALID_CHUNK_RESPONSE + "\n```"
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
    def _patch_httpx(self):
        self.mock_post = AsyncMock(return_value=_make_httpx_response(VALID_CHUNK_RESPONSE))
        mock_client = AsyncMock()
        mock_client.post = self.mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.analyzer.httpx.AsyncClient", return_value=mock_client):
            self.mock_client = mock_client
            yield

    async def test_returns_partial_result(self):
        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.analyze_chunk(_make_chunk())
        assert isinstance(result, PartialResult)
        assert result.chunk_index == 0
        assert len(result.topics_found) == 1

    async def test_calls_model_with_prompt(self):
        svc = AnalyzerService(api_key="test-key", max_retries=3)
        await svc.analyze_chunk(_make_chunk())
        self.mock_post.assert_called_once()
        call_kwargs = self.mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        prompt_text = body["messages"][0]["content"]
        assert "topics_found" in prompt_text


# ---------------------------------------------------------------------------
# AnalyzerService.analyze_chunk — retry on invalid JSON
# ---------------------------------------------------------------------------


class TestAnalyzeChunkRetryInvalidJson:
    @pytest.fixture(autouse=True)
    def _patch_httpx(self):
        self.mock_post = AsyncMock()
        mock_client = AsyncMock()
        mock_client.post = self.mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.analyzer.httpx.AsyncClient", return_value=mock_client):
            self.mock_client = mock_client
            yield

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_retries_on_invalid_json_then_succeeds(self, mock_sleep):
        bad = _make_httpx_response("not json")
        good = _make_httpx_response(VALID_CHUNK_RESPONSE)
        self.mock_post.side_effect = [bad, good]

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.analyze_chunk(_make_chunk())
        assert isinstance(result, PartialResult)
        assert self.mock_post.call_count == 2
        mock_sleep.assert_called_once_with(2)

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_raises_after_all_retries_invalid_json(self, mock_sleep):
        self.mock_post.return_value = _make_httpx_response("bad")

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        with pytest.raises(AnalyzerError, match="unavailable after 3 attempts"):
            await svc.analyze_chunk(_make_chunk())
        assert self.mock_post.call_count == 3


# ---------------------------------------------------------------------------
# AnalyzerService.analyze_chunk — retry on API errors
# ---------------------------------------------------------------------------


class TestAnalyzeChunkRetryApiError:
    @pytest.fixture(autouse=True)
    def _patch_httpx(self):
        self.mock_post = AsyncMock()
        mock_client = AsyncMock()
        mock_client.post = self.mock_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.analyzer.httpx.AsyncClient", return_value=mock_client):
            self.mock_client = mock_client
            yield

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_retries_on_connection_error_then_succeeds(self, mock_sleep):
        good = _make_httpx_response(VALID_CHUNK_RESPONSE)
        self.mock_post.side_effect = [
            httpx.ConnectError("network"),
            good,
        ]

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.analyze_chunk(_make_chunk())
        assert isinstance(result, PartialResult)
        mock_sleep.assert_called_once_with(2)

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_exponential_backoff_delays(self, mock_sleep):
        good = _make_httpx_response(VALID_CHUNK_RESPONSE)
        self.mock_post.side_effect = [
            httpx.ConnectError("err1"),
            httpx.TimeoutException("err2"),
            good,
        ]

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        result = await svc.analyze_chunk(_make_chunk())
        assert isinstance(result, PartialResult)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    @patch("app.services.analyzer.asyncio.sleep", return_value=None)
    async def test_raises_analyzer_error_after_all_retries(self, mock_sleep):
        self.mock_post.side_effect = httpx.ConnectError("down")

        svc = AnalyzerService(api_key="test-key", max_retries=3)
        with pytest.raises(AnalyzerError, match="unavailable after 3 attempts"):
            await svc.analyze_chunk(_make_chunk())
        assert self.mock_post.call_count == 3
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
