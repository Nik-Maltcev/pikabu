"""Tests for the REST API router (task 9.1).

Uses FastAPI TestClient with a mocked async DB session and services.
Covers: GET /api/topics, POST /api/analysis/start,
        GET /api/analysis/status/{task_id},
        GET /api/reports/{topic_id}, GET /api/reports/{topic_id}/{report_id}
Error handling: 400, 404, 409
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app
from app.models.database import AnalysisTask, Report as DBReport, Topic as DBTopic


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_topic(
    id: int = 1,
    pikabu_id: str = "community_1",
    name: str = "Test Topic",
    subscribers_count: int = 100,
    url: str = "https://pikabu.ru/community/test",
    last_fetched_at: datetime | None = None,
    source: str = "pikabu",
) -> DBTopic:
    t = DBTopic()
    t.id = id
    t.pikabu_id = pikabu_id
    t.name = name
    t.subscribers_count = subscribers_count
    t.url = url
    t.last_fetched_at = last_fetched_at or datetime.now(timezone.utc)
    t.source = source
    return t


def _make_task(
    topic_id: int = 1,
    status: str = "completed",
    progress_percent: int = 100,
    current_stage: str | None = "completed",
    task_id: uuid.UUID | None = None,
) -> AnalysisTask:
    t = AnalysisTask()
    t.id = task_id or uuid.uuid4()
    t.topic_id = topic_id
    t.status = status
    t.progress_percent = progress_percent
    t.current_stage = current_stage
    t.total_chunks = 3
    t.processed_chunks = 3
    t.error_message = None
    return t


def _make_report(
    id: int = 1,
    topic_id: int = 1,
    task_id: uuid.UUID | None = None,
    sources: str = "pikabu",
) -> DBReport:
    r = DBReport()
    r.id = id
    r.topic_id = topic_id
    r.task_id = task_id or uuid.uuid4()
    r.hot_topics = [{"name": "AI", "description": "Artificial Intelligence", "mentions_count": 42}]
    r.user_problems = [{"description": "Slow loading", "examples": ["page takes 10s"]}]
    r.trending_discussions = [
        {"title": "GPT-5", "description": "Discussion about GPT-5",
         "post_url": "https://pikabu.ru/1", "activity_score": 9.5}
    ]
    r.generated_at = datetime.now(timezone.utc)
    r.sources = sources
    return r


# ---------------------------------------------------------------------------
# Mock DB session helper
# ---------------------------------------------------------------------------

class _FakeScalarResult:
    """Mimics the result of session.execute(...).scalar_one_or_none()."""

    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeScalarsResult:
    """Mimics result.scalars().all()."""

    def __init__(self, items: list):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None


def _build_mock_session():
    """Return an AsyncMock that behaves like an AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session():
    return _build_mock_session()


@pytest.fixture
def client(mock_session):
    """TestClient with the DB session dependency overridden."""

    async def _override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = _override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


# ===========================================================================
# GET /api/topics
# ===========================================================================

class TestGetTopics:
    """Tests for GET /api/topics endpoint."""

    def test_returns_topics_list(self, client, mock_session):
        """Should return a list of topics from TopicManager."""
        topics = [_make_topic(id=1, name="Python"), _make_topic(id=2, name="JavaScript")]

        with patch("app.api.router.TopicManager") as MockTM:
            instance = MockTM.return_value
            instance.fetch_topics = AsyncMock(return_value=topics)
            MockTM.filter_topics = MagicMock(return_value=topics)

            resp = client.get("/api/topics")

        assert resp.status_code == 200
        data = resp.json()
        assert "topics" in data
        assert len(data["topics"]) == 2
        assert data["topics"][0]["name"] == "Python"
        assert data["topics"][1]["name"] == "JavaScript"
        # Verify source field is present
        assert data["topics"][0]["source"] == "pikabu"

    def test_returns_empty_list_when_no_topics(self, client, mock_session):
        """Should return empty list when no topics available."""
        with patch("app.api.router.TopicManager") as MockTM:
            instance = MockTM.return_value
            instance.fetch_topics = AsyncMock(return_value=[])

            resp = client.get("/api/topics")

        assert resp.status_code == 200
        assert resp.json()["topics"] == []

    def test_search_filter_applied(self, client, mock_session):
        """Should filter topics when search query param is provided."""
        all_topics = [_make_topic(id=1, name="Python"), _make_topic(id=2, name="JavaScript")]
        filtered = [_make_topic(id=1, name="Python")]

        with patch("app.api.router.TopicManager") as MockTM:
            instance = MockTM.return_value
            instance.fetch_topics = AsyncMock(return_value=all_topics)
            MockTM.filter_topics = MagicMock(return_value=filtered)

            resp = client.get("/api/topics?search=Pyth")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["topics"]) == 1
        assert data["topics"][0]["name"] == "Python"
        MockTM.filter_topics.assert_called_once_with(all_topics, "Pyth")

    def test_empty_search_returns_all(self, client, mock_session):
        """Empty search string should return all topics (no filtering)."""
        topics = [_make_topic(id=1, name="Python")]

        with patch("app.api.router.TopicManager") as MockTM:
            instance = MockTM.return_value
            instance.fetch_topics = AsyncMock(return_value=topics)

            resp = client.get("/api/topics?search=")

        assert resp.status_code == 200
        assert len(resp.json()["topics"]) == 1

    def test_topic_schema_fields(self, client, mock_session):
        """Response topics should contain all required fields."""
        topic = _make_topic(id=5, pikabu_id="comm_5", name="Rust", subscribers_count=999,
                            url="https://pikabu.ru/community/rust")

        with patch("app.api.router.TopicManager") as MockTM:
            instance = MockTM.return_value
            instance.fetch_topics = AsyncMock(return_value=[topic])

            resp = client.get("/api/topics")

        t = resp.json()["topics"][0]
        assert t["id"] == 5
        assert t["pikabu_id"] == "comm_5"
        assert t["name"] == "Rust"
        assert t["subscribers_count"] == 999
        assert t["url"] == "https://pikabu.ru/community/rust"


# ===========================================================================
# POST /api/analysis/start
# ===========================================================================

class TestStartAnalysis:
    """Tests for POST /api/analysis/start endpoint."""

    def test_start_analysis_success(self, client, mock_session):
        """Should create a task and return task_id with status pending."""
        topic = _make_topic(id=1)
        task_id = uuid.uuid4()

        # session.execute for topic lookup
        mock_session.execute = AsyncMock(return_value=_FakeScalarResult(topic))

        # Capture the task added to session to set its id
        def _capture_add(obj):
            if isinstance(obj, AnalysisTask):
                obj.id = task_id

        mock_session.add = MagicMock(side_effect=_capture_add)

        with patch("app.api.router.asyncio") as mock_asyncio:
            mock_asyncio.create_task = MagicMock()
            resp = client.post("/api/analysis/start", json={"topic_id": 1})

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == str(task_id)
        assert data["status"] == "pending"

    def test_start_analysis_topic_not_found(self, client, mock_session):
        """Should return 404 when topic_id doesn't exist."""
        mock_session.execute = AsyncMock(return_value=_FakeScalarResult(None))

        resp = client.post("/api/analysis/start", json={"topic_id": 999})

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_start_analysis_missing_topic_id(self, client, mock_session):
        """Should return 422 when topic_id is missing from request body."""
        resp = client.post("/api/analysis/start", json={})
        assert resp.status_code == 422

    def test_start_analysis_invalid_topic_id_type(self, client, mock_session):
        """Should return 422 when topic_id is not an integer."""
        resp = client.post("/api/analysis/start", json={"topic_id": "not_a_number"})
        assert resp.status_code == 422


# ===========================================================================
# GET /api/analysis/status/{task_id}
# ===========================================================================

class TestAnalysisStatus:
    """Tests for GET /api/analysis/status/{task_id} endpoint."""

    def test_status_completed_with_report(self, client, mock_session):
        """Should return task status and report_id when completed."""
        task = _make_task(status="completed", progress_percent=100)
        report_id = 42

        call_count = 0

        async def _execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: task lookup
                return _FakeScalarResult(task)
            else:
                # Second call: report_id lookup
                return _FakeScalarResult(report_id)

        mock_session.execute = AsyncMock(side_effect=_execute_side_effect)

        resp = client.get(f"/api/analysis/status/{task.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == str(task.id)
        assert data["status"] == "completed"
        assert data["progress_percent"] == 100
        assert data["report_id"] == 42

    def test_status_pending_no_report(self, client, mock_session):
        """Should return task status without report_id when pending."""
        task = _make_task(status="pending", progress_percent=0, current_stage="pending")
        task.processed_chunks = 0
        task.total_chunks = None

        mock_session.execute = AsyncMock(return_value=_FakeScalarResult(task))

        resp = client.get(f"/api/analysis/status/{task.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["progress_percent"] == 0
        assert data["report_id"] is None

    def test_status_task_not_found(self, client, mock_session):
        """Should return 404 when task_id doesn't exist."""
        mock_session.execute = AsyncMock(return_value=_FakeScalarResult(None))

        fake_id = uuid.uuid4()
        resp = client.get(f"/api/analysis/status/{fake_id}")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_status_invalid_uuid(self, client, mock_session):
        """Should return 422 when task_id is not a valid UUID."""
        resp = client.get("/api/analysis/status/not-a-uuid")
        assert resp.status_code == 422

    def test_status_failed_task(self, client, mock_session):
        """Should return error_message for failed tasks."""
        task = _make_task(status="failed", progress_percent=50, current_stage="failed")
        task.error_message = "Gemini API unavailable"

        mock_session.execute = AsyncMock(return_value=_FakeScalarResult(task))

        resp = client.get(f"/api/analysis/status/{task.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Gemini API unavailable"

    def test_status_chunk_analysis_in_progress(self, client, mock_session):
        """Should return chunk progress during analysis."""
        task = _make_task(status="chunk_analysis", progress_percent=60, current_stage="chunk_analysis")
        task.total_chunks = 10
        task.processed_chunks = 6

        mock_session.execute = AsyncMock(return_value=_FakeScalarResult(task))

        resp = client.get(f"/api/analysis/status/{task.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "chunk_analysis"
        assert data["total_chunks"] == 10
        assert data["processed_chunks"] == 6
        assert data["progress_percent"] == 60


# ===========================================================================
# GET /api/reports/{topic_id}
# ===========================================================================

class TestGetReports:
    """Tests for GET /api/reports/{topic_id} endpoint."""

    def test_returns_reports_for_topic(self, client, mock_session):
        """Should return list of reports for a valid topic."""
        topic = _make_topic(id=1)
        reports = [_make_report(id=1, topic_id=1), _make_report(id=2, topic_id=1)]

        call_count = 0

        async def _execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _FakeScalarResult(topic)
            else:
                return _FakeScalarsResult(reports)

        mock_session.execute = AsyncMock(side_effect=_execute_side_effect)

        resp = client.get("/api/reports/1")

        assert resp.status_code == 200
        data = resp.json()
        assert "reports" in data
        assert len(data["reports"]) == 2

    def test_returns_empty_list_for_topic_with_no_reports(self, client, mock_session):
        """Should return empty reports list for topic with no reports."""
        topic = _make_topic(id=1)

        call_count = 0

        async def _execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _FakeScalarResult(topic)
            else:
                return _FakeScalarsResult([])

        mock_session.execute = AsyncMock(side_effect=_execute_side_effect)

        resp = client.get("/api/reports/1")

        assert resp.status_code == 200
        assert resp.json()["reports"] == []

    def test_topic_not_found(self, client, mock_session):
        """Should return 404 when topic doesn't exist."""
        mock_session.execute = AsyncMock(return_value=_FakeScalarResult(None))

        resp = client.get("/api/reports/999")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_report_schema_fields(self, client, mock_session):
        """Report objects should contain all required fields."""
        topic = _make_topic(id=1)
        report = _make_report(id=10, topic_id=1)

        call_count = 0

        async def _execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _FakeScalarResult(topic)
            else:
                return _FakeScalarsResult([report])

        mock_session.execute = AsyncMock(side_effect=_execute_side_effect)

        resp = client.get("/api/reports/1")

        r = resp.json()["reports"][0]
        assert r["id"] == 10
        assert r["topic_id"] == 1
        assert isinstance(r["hot_topics"], list)
        assert isinstance(r["user_problems"], list)
        assert isinstance(r["trending_discussions"], list)
        assert "generated_at" in r


# ===========================================================================
# GET /api/reports/{topic_id}/{report_id}
# ===========================================================================

class TestGetReport:
    """Tests for GET /api/reports/{topic_id}/{report_id} endpoint."""

    def test_returns_specific_report(self, client, mock_session):
        """Should return a specific report by topic_id and report_id."""
        report = _make_report(id=5, topic_id=1)
        mock_session.execute = AsyncMock(return_value=_FakeScalarResult(report))

        resp = client.get("/api/reports/1/5")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 5
        assert data["topic_id"] == 1
        assert len(data["hot_topics"]) == 1
        assert data["hot_topics"][0]["name"] == "AI"

    def test_report_not_found(self, client, mock_session):
        """Should return 404 when report doesn't exist."""
        mock_session.execute = AsyncMock(return_value=_FakeScalarResult(None))

        resp = client.get("/api/reports/1/999")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_report_wrong_topic(self, client, mock_session):
        """Should return 404 when report exists but for different topic."""
        mock_session.execute = AsyncMock(return_value=_FakeScalarResult(None))

        resp = client.get("/api/reports/2/5")

        assert resp.status_code == 404

    def test_report_detail_fields(self, client, mock_session):
        """Report detail should include all sub-model fields."""
        report = _make_report(id=1, topic_id=1)
        mock_session.execute = AsyncMock(return_value=_FakeScalarResult(report))

        resp = client.get("/api/reports/1/1")

        data = resp.json()
        # hot_topics
        ht = data["hot_topics"][0]
        assert "name" in ht
        assert "description" in ht
        assert "mentions_count" in ht
        # user_problems
        up = data["user_problems"][0]
        assert "description" in up
        assert "examples" in up
        # trending_discussions
        td = data["trending_discussions"][0]
        assert "title" in td
        assert "description" in td
        assert "post_url" in td
        assert "activity_score" in td


# ===========================================================================
# JSON response format
# ===========================================================================

class TestJsonResponseFormat:
    """Verify all endpoints return JSON (Requirement 8.6)."""

    def test_topics_returns_json(self, client, mock_session):
        with patch("app.api.router.TopicManager") as MockTM:
            instance = MockTM.return_value
            instance.fetch_topics = AsyncMock(return_value=[])
            resp = client.get("/api/topics")
        assert resp.headers["content-type"].startswith("application/json")

    def test_status_returns_json(self, client, mock_session):
        task = _make_task()
        call_count = 0

        async def _execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _FakeScalarResult(task)
            else:
                return _FakeScalarResult(None)

        mock_session.execute = AsyncMock(side_effect=_execute_side_effect)
        resp = client.get(f"/api/analysis/status/{task.id}")
        assert resp.headers["content-type"].startswith("application/json")

    def test_reports_list_returns_json(self, client, mock_session):
        topic = _make_topic(id=1)
        call_count = 0

        async def _execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _FakeScalarResult(topic)
            else:
                return _FakeScalarsResult([])

        mock_session.execute = AsyncMock(side_effect=_execute_side_effect)
        resp = client.get("/api/reports/1")
        assert resp.headers["content-type"].startswith("application/json")

    def test_report_detail_returns_json(self, client, mock_session):
        report = _make_report(id=1, topic_id=1)
        mock_session.execute = AsyncMock(return_value=_FakeScalarResult(report))
        resp = client.get("/api/reports/1/1")
        assert resp.headers["content-type"].startswith("application/json")
