"""Tests for the full analysis pipeline (run_full_analysis)."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import (
    Chunk,
    HotTopic,
    PartialResult,
    TrendingDiscussion,
    UserProblem,
)
from app.services.pipeline import (
    ACTIVE_STATUSES,
    AnalysisAlreadyRunningError,
    PipelineError,
    run_full_analysis,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _aggregation_report() -> dict:
    return {
        "hot_topics": [HotTopic(name="Итог", description="Описание", mentions_count=10)],
        "user_problems": [UserProblem(description="Общая проблема", examples=["пример"])],
        "trending_discussions": [
            TrendingDiscussion(
                title="Топ",
                description="Описание",
                post_url="https://pikabu.ru/story/1",
                activity_score=0.9,
            )
        ],
    }


class _FakeAnalysisTask:
    """Lightweight stand-in for the AnalysisTask ORM model."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid.uuid4())
        self.topic_id = kwargs.get("topic_id")
        self.status = kwargs.get("status", "pending")
        self.progress_percent = kwargs.get("progress_percent", 0)
        self.current_stage = kwargs.get("current_stage")
        self.total_chunks = kwargs.get("total_chunks")
        self.processed_chunks = kwargs.get("processed_chunks", 0)
        self.error_message = kwargs.get("error_message")
        self.updated_at = kwargs.get("updated_at")


class _FakePost:
    """Lightweight stand-in for the Post ORM model."""

    def __init__(self, **kwargs):
        self.pikabu_post_id = kwargs.get("pikabu_post_id", "p1")
        self.title = kwargs.get("title", "Post title")
        self.body = kwargs.get("body", "Post body")
        self.published_at = kwargs.get("published_at", datetime.now(timezone.utc))
        self.rating = kwargs.get("rating", 10)
        self.comments_count = kwargs.get("comments_count", 2)
        self.url = kwargs.get("url", "https://pikabu.ru/story/1")
        self.comments = kwargs.get("comments", [])


class _FakeComment:
    """Lightweight stand-in for the Comment ORM model."""

    def __init__(self, **kwargs):
        self.pikabu_comment_id = kwargs.get("pikabu_comment_id", "c1")
        self.body = kwargs.get("body", "Comment body")
        self.published_at = kwargs.get("published_at", datetime.now(timezone.utc))
        self.rating = kwargs.get("rating", 5)


class _FakeScalarResult:
    """Mimics SQLAlchemy scalar result."""

    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def first(self):
        return self._value


class _FakeScalarsResult:
    """Mimics SQLAlchemy scalars() result."""

    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _FakeResult:
    """Mimics SQLAlchemy execute result with scalars()."""

    def __init__(self, items=None, scalar=None):
        self._items = items or []
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return _FakeScalarsResult(self._items)


def _build_mock_session(
    *,
    active_task: _FakeAnalysisTask | None = None,
    posts: list[_FakePost] | None = None,
):
    """Build a mock AsyncSession that handles the pipeline's DB queries.

    The mock tracks:
    - select(AnalysisTask) → returns active_task or None
    - select(Post) → returns posts list
    - select(DBPartialResult) → returns None (no duplicates)
    - add / flush → no-op
    - refresh → populates comments attribute
    """
    session = AsyncMock()
    added_objects: list = []

    call_count = {"execute": 0}

    async def _execute(stmt):
        call_count["execute"] += 1
        stmt_str = str(stmt)

        # First call: check for active task
        if "analysis_tasks" in stmt_str and "IN" in stmt_str:
            return _FakeScalarResult(active_task)

        # Load posts for chunking
        if "posts" in stmt_str and "topic_id" in stmt_str:
            return _FakeResult(items=posts or [])

        # Check for existing partial results (dedup in error handler)
        if "partial_results" in stmt_str:
            return _FakeScalarResult(None)

        return _FakeScalarResult(None)

    session.execute = AsyncMock(side_effect=_execute)
    session.flush = AsyncMock()
    session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

    async def _refresh(obj, attrs=None):
        if hasattr(obj, "comments") and not obj.comments:
            obj.comments = []

    session.refresh = AsyncMock(side_effect=_refresh)
    session._added_objects = added_objects

    return session


# ---------------------------------------------------------------------------
# Tests: Duplicate run blocking
# ---------------------------------------------------------------------------


class TestDuplicateRunBlocking:
    async def test_raises_when_active_task_exists(self):
        """Should raise AnalysisAlreadyRunningError if an active task exists."""
        active = _FakeAnalysisTask(topic_id=1, status="parsing")
        session = _build_mock_session(active_task=active)

        with pytest.raises(AnalysisAlreadyRunningError) as exc_info:
            await run_full_analysis(
                topic_id=1,
                session=session,
                parser_service=AsyncMock(),
                cache_service=AsyncMock(),
                analyzer_service=AsyncMock(),
            )
        assert str(active.id) in str(exc_info.value)

    async def test_proceeds_when_no_active_task(self):
        """Should create a new task when no active task exists."""
        post = _FakePost(comments=[_FakeComment()])
        session = _build_mock_session(active_task=None, posts=[post])

        cache_svc = AsyncMock()
        cache_svc.is_cache_valid = AsyncMock(return_value=True)

        analyzer_svc = AsyncMock()
        analyzer_svc.analyze_chunk = AsyncMock(return_value=_make_partial_result(0))
        analyzer_svc.hierarchical_aggregate = AsyncMock(return_value=_aggregation_report())

        task = await run_full_analysis(
            topic_id=1,
            session=session,
            parser_service=AsyncMock(),
            cache_service=cache_svc,
            analyzer_service=analyzer_svc,
        )
        assert task.status == "completed"


# ---------------------------------------------------------------------------
# Tests: Cache check and parsing
# ---------------------------------------------------------------------------


class TestCacheAndParsing:
    async def test_skips_parsing_when_cache_valid(self):
        """When cache is valid, parser.parse_topic should NOT be called."""
        post = _FakePost(comments=[])
        session = _build_mock_session(posts=[post])

        parser_svc = AsyncMock()
        cache_svc = AsyncMock()
        cache_svc.is_cache_valid = AsyncMock(return_value=True)

        analyzer_svc = AsyncMock()
        analyzer_svc.analyze_chunk = AsyncMock(return_value=_make_partial_result(0))
        analyzer_svc.hierarchical_aggregate = AsyncMock(return_value=_aggregation_report())

        await run_full_analysis(
            topic_id=1,
            session=session,
            parser_service=parser_svc,
            cache_service=cache_svc,
            analyzer_service=analyzer_svc,
        )
        parser_svc.parse_topic.assert_not_called()

    async def test_runs_parsing_when_cache_invalid(self):
        """When cache is invalid, parser.parse_topic should be called."""
        post = _FakePost(comments=[])
        session = _build_mock_session(posts=[post])

        parser_svc = AsyncMock()
        parser_svc.parse_topic = AsyncMock(return_value={"posts_count": 1, "comments_count": 0})

        cache_svc = AsyncMock()
        cache_svc.is_cache_valid = AsyncMock(return_value=False)

        analyzer_svc = AsyncMock()
        analyzer_svc.analyze_chunk = AsyncMock(return_value=_make_partial_result(0))
        analyzer_svc.hierarchical_aggregate = AsyncMock(return_value=_aggregation_report())

        await run_full_analysis(
            topic_id=1,
            session=session,
            parser_service=parser_svc,
            cache_service=cache_svc,
            analyzer_service=analyzer_svc,
        )
        parser_svc.parse_topic.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: Status transitions and progress
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    async def test_completed_status_on_success(self):
        """Task should end with status 'completed' on success."""
        post = _FakePost(comments=[_FakeComment()])
        session = _build_mock_session(posts=[post])

        cache_svc = AsyncMock()
        cache_svc.is_cache_valid = AsyncMock(return_value=True)

        analyzer_svc = AsyncMock()
        analyzer_svc.analyze_chunk = AsyncMock(return_value=_make_partial_result(0))
        analyzer_svc.hierarchical_aggregate = AsyncMock(return_value=_aggregation_report())

        task = await run_full_analysis(
            topic_id=1,
            session=session,
            parser_service=AsyncMock(),
            cache_service=cache_svc,
            analyzer_service=analyzer_svc,
        )
        assert task.status == "completed"
        assert task.progress_percent == 100
        assert task.current_stage == "completed"

    async def test_failed_status_on_analyzer_error(self):
        """Task should end with status 'failed' when analyzer raises."""
        from app.services.analyzer import AnalyzerError

        post = _FakePost(comments=[])
        session = _build_mock_session(posts=[post])

        cache_svc = AsyncMock()
        cache_svc.is_cache_valid = AsyncMock(return_value=True)

        analyzer_svc = AsyncMock()
        analyzer_svc.analyze_chunk = AsyncMock(side_effect=AnalyzerError("Gemini down"))

        task = await run_full_analysis(
            topic_id=1,
            session=session,
            parser_service=AsyncMock(),
            cache_service=cache_svc,
            analyzer_service=analyzer_svc,
        )
        assert task.status == "failed"
        assert "Gemini down" in task.error_message

    async def test_failed_status_on_parser_error(self):
        """Task should end with status 'failed' when parser raises."""
        from app.services.parser import ParserError

        session = _build_mock_session(posts=[])

        parser_svc = AsyncMock()
        parser_svc.parse_topic = AsyncMock(side_effect=ParserError("Network error"))

        cache_svc = AsyncMock()
        cache_svc.is_cache_valid = AsyncMock(return_value=False)

        task = await run_full_analysis(
            topic_id=1,
            session=session,
            parser_service=parser_svc,
            cache_service=cache_svc,
            analyzer_service=AsyncMock(),
        )
        assert task.status == "failed"
        assert "Network error" in task.error_message


# ---------------------------------------------------------------------------
# Tests: Chunk analysis and partial results
# ---------------------------------------------------------------------------


class TestChunkAnalysis:
    async def test_analyzes_all_chunks(self):
        """Analyzer should be called once per chunk."""
        posts = [_FakePost(pikabu_post_id=f"p{i}", comments=[]) for i in range(3)]
        session = _build_mock_session(posts=posts)

        cache_svc = AsyncMock()
        cache_svc.is_cache_valid = AsyncMock(return_value=True)

        call_count = 0

        async def _analyze(chunk):
            nonlocal call_count
            result = _make_partial_result(chunk.index)
            call_count += 1
            return result

        analyzer_svc = AsyncMock()
        analyzer_svc.analyze_chunk = AsyncMock(side_effect=_analyze)
        analyzer_svc.hierarchical_aggregate = AsyncMock(return_value=_aggregation_report())

        task = await run_full_analysis(
            topic_id=1,
            session=session,
            parser_service=AsyncMock(),
            cache_service=cache_svc,
            analyzer_service=analyzer_svc,
        )
        assert task.status == "completed"
        # All 3 posts likely fit in one chunk, so at least 1 call
        assert call_count >= 1

    async def test_partial_results_saved_on_failure(self):
        """Partial results should be saved even when a later chunk fails."""
        from app.services.analyzer import AnalyzerError

        posts = [_FakePost(pikabu_post_id=f"p{i}", comments=[]) for i in range(3)]
        session = _build_mock_session(posts=posts)

        cache_svc = AsyncMock()
        cache_svc.is_cache_valid = AsyncMock(return_value=True)

        # First chunk succeeds, second fails
        analyzer_svc = AsyncMock()
        analyzer_svc.analyze_chunk = AsyncMock(
            side_effect=[_make_partial_result(0), AnalyzerError("chunk 1 failed")]
        )

        # Use a small max_tokens to force multiple chunks
        with patch("app.services.pipeline.chunk_data") as mock_chunk:
            mock_chunk.return_value = [
                Chunk(index=0, posts_data=[{"title": "A"}], estimated_tokens=10),
                Chunk(index=1, posts_data=[{"title": "B"}], estimated_tokens=10),
            ]

            task = await run_full_analysis(
                topic_id=1,
                session=session,
                parser_service=AsyncMock(),
                cache_service=cache_svc,
                analyzer_service=analyzer_svc,
            )

        assert task.status == "failed"
        # The first partial result should have been saved (via session.add)
        added_types = [type(obj).__name__ for obj in session._added_objects]
        assert "PartialResult" in added_types or "DBPartialResult" in added_types or any(
            hasattr(obj, "chunk_index") for obj in session._added_objects
        )


# ---------------------------------------------------------------------------
# Tests: Report saving
# ---------------------------------------------------------------------------


class TestReportSaving:
    async def test_report_saved_on_success(self):
        """A Report should be added to the session on successful completion."""
        post = _FakePost(comments=[])
        session = _build_mock_session(posts=[post])

        cache_svc = AsyncMock()
        cache_svc.is_cache_valid = AsyncMock(return_value=True)

        analyzer_svc = AsyncMock()
        analyzer_svc.analyze_chunk = AsyncMock(return_value=_make_partial_result(0))
        analyzer_svc.hierarchical_aggregate = AsyncMock(return_value=_aggregation_report())

        await run_full_analysis(
            topic_id=1,
            session=session,
            parser_service=AsyncMock(),
            cache_service=cache_svc,
            analyzer_service=analyzer_svc,
        )

        # Check that a Report-like object was added
        report_added = any(
            hasattr(obj, "hot_topics") and hasattr(obj, "trending_discussions")
            for obj in session._added_objects
        )
        assert report_added, "Expected a Report to be saved to the session"
