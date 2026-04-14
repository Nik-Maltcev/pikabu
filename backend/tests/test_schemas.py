"""Tests for Pydantic API schemas."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AnalysisStartRequest,
    AnalysisStartResponse,
    AnalysisStatusResponse,
    Chunk,
    HotTopic,
    PartialResult,
    Report,
    ReportListResponse,
    Topic,
    TopicListResponse,
    TrendingDiscussion,
    UserProblem,
)


# --- HotTopic ---


class TestHotTopic:
    def test_valid(self):
        ht = HotTopic(name="AI", description="Artificial intelligence", mentions_count=42)
        assert ht.name == "AI"
        assert ht.mentions_count == 42

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            HotTopic(name="AI", description="desc")  # missing mentions_count


# --- UserProblem ---


class TestUserProblem:
    def test_valid(self):
        up = UserProblem(description="Slow loading", examples=["page takes 10s", "timeout"])
        assert up.description == "Slow loading"
        assert len(up.examples) == 2

    def test_empty_examples(self):
        up = UserProblem(description="Bug", examples=[])
        assert up.examples == []

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            UserProblem(description="Bug")  # missing examples


# --- TrendingDiscussion ---


class TestTrendingDiscussion:
    def test_valid(self):
        td = TrendingDiscussion(
            title="Hot debate",
            description="People argue",
            post_url="https://pikabu.ru/story/123",
            activity_score=9.5,
        )
        assert td.activity_score == 9.5

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            TrendingDiscussion(title="X", description="Y", post_url="url")  # missing activity_score


# --- Topic ---


class TestTopic:
    def test_valid_with_subscribers(self):
        t = Topic(id=1, pikabu_id="abc", name="Python", subscribers_count=1000, url="https://pikabu.ru/community/python")
        assert t.subscribers_count == 1000

    def test_valid_without_subscribers(self):
        t = Topic(id=2, pikabu_id="xyz", name="Rust", subscribers_count=None, url="https://pikabu.ru/tag/rust")
        assert t.subscribers_count is None

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            Topic(id=1, pikabu_id="abc", name="Python")  # missing url


# --- TopicListResponse ---


class TestTopicListResponse:
    def test_valid(self):
        resp = TopicListResponse(topics=[
            Topic(id=1, pikabu_id="a", name="A", subscribers_count=10, url="https://a"),
        ])
        assert len(resp.topics) == 1

    def test_empty_list(self):
        resp = TopicListResponse(topics=[])
        assert resp.topics == []


# --- AnalysisStartRequest ---


class TestAnalysisStartRequest:
    def test_valid(self):
        req = AnalysisStartRequest(topic_id=42)
        assert req.topic_id == 42

    def test_missing_topic_id_raises(self):
        with pytest.raises(ValidationError):
            AnalysisStartRequest()


# --- AnalysisStartResponse ---


class TestAnalysisStartResponse:
    def test_valid(self):
        tid = uuid4()
        resp = AnalysisStartResponse(task_id=tid, status="started")
        assert resp.task_id == tid
        assert resp.status == "started"


# --- AnalysisStatusResponse ---


class TestAnalysisStatusResponse:
    def test_full(self):
        tid = uuid4()
        resp = AnalysisStatusResponse(
            task_id=tid,
            status="chunk_analysis",
            progress_percent=50,
            current_stage="Analyzing chunk 3 of 6",
            total_chunks=6,
            processed_chunks=3,
            error_message=None,
            report_id=None,
        )
        assert resp.progress_percent == 50

    def test_completed_with_report(self):
        resp = AnalysisStatusResponse(
            task_id=uuid4(),
            status="completed",
            progress_percent=100,
            current_stage=None,
            total_chunks=4,
            processed_chunks=4,
            error_message=None,
            report_id=7,
        )
        assert resp.report_id == 7

    def test_failed_with_error(self):
        resp = AnalysisStatusResponse(
            task_id=uuid4(),
            status="failed",
            progress_percent=30,
            current_stage=None,
            total_chunks=10,
            processed_chunks=3,
            error_message="Gemini API unavailable",
            report_id=None,
        )
        assert resp.error_message == "Gemini API unavailable"


# --- Report ---


class TestReport:
    def test_valid(self):
        now = datetime.now(timezone.utc)
        r = Report(
            id=1,
            topic_id=5,
            hot_topics=[HotTopic(name="T", description="D", mentions_count=1)],
            user_problems=[],
            trending_discussions=[],
            generated_at=now,
        )
        assert r.id == 1
        assert len(r.hot_topics) == 1

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            Report(id=1, topic_id=5, hot_topics=[], user_problems=[])  # missing fields


# --- ReportListResponse ---


class TestReportListResponse:
    def test_valid(self):
        now = datetime.now(timezone.utc)
        resp = ReportListResponse(reports=[
            Report(id=1, topic_id=1, hot_topics=[], user_problems=[], trending_discussions=[], generated_at=now),
        ])
        assert len(resp.reports) == 1


# --- Chunk ---


class TestChunk:
    def test_valid(self):
        c = Chunk(index=0, posts_data=[{"title": "Hello"}], estimated_tokens=500)
        assert c.index == 0
        assert c.estimated_tokens == 500

    def test_empty_posts(self):
        c = Chunk(index=1, posts_data=[], estimated_tokens=0)
        assert c.posts_data == []


# --- PartialResult ---


class TestPartialResult:
    def test_valid(self):
        pr = PartialResult(
            chunk_index=0,
            topics_found=[HotTopic(name="T", description="D", mentions_count=3)],
            user_problems=[UserProblem(description="P", examples=["e1"])],
            active_discussions=[
                TrendingDiscussion(title="D", description="X", post_url="url", activity_score=1.0)
            ],
        )
        assert pr.chunk_index == 0
        assert len(pr.topics_found) == 1
        assert len(pr.user_problems) == 1
        assert len(pr.active_discussions) == 1

    def test_empty_lists(self):
        pr = PartialResult(
            chunk_index=5,
            topics_found=[],
            user_problems=[],
            active_discussions=[],
        )
        assert pr.topics_found == []


# --- JSON round-trip ---


class TestJsonRoundTrip:
    def test_report_serialization(self):
        now = datetime.now(timezone.utc)
        r = Report(
            id=1,
            topic_id=2,
            hot_topics=[HotTopic(name="N", description="D", mentions_count=10)],
            user_problems=[UserProblem(description="P", examples=["a", "b"])],
            trending_discussions=[
                TrendingDiscussion(title="T", description="D", post_url="u", activity_score=5.5)
            ],
            generated_at=now,
        )
        data = r.model_dump(mode="json")
        restored = Report.model_validate(data)
        assert restored == r

    def test_partial_result_serialization(self):
        pr = PartialResult(
            chunk_index=0,
            topics_found=[HotTopic(name="N", description="D", mentions_count=1)],
            user_problems=[],
            active_discussions=[],
        )
        data = pr.model_dump(mode="json")
        restored = PartialResult.model_validate(data)
        assert restored == pr
