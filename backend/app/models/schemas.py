"""Pydantic models for API request/response and internal data structures."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# --- Report sub-models ---


class HotTopic(BaseModel):
    """A frequently discussed topic found during analysis."""

    name: str
    description: str
    mentions_count: int


class UserProblem(BaseModel):
    """A user problem identified during analysis."""

    description: str
    examples: list[str]


class TrendingDiscussion(BaseModel):
    """A trending discussion with a link to the original post."""

    title: str
    description: str
    post_url: str
    activity_score: float


# --- Topic models ---


class Topic(BaseModel):
    """A Pikabu topic (community/tag)."""

    id: int
    pikabu_id: str
    name: str
    subscribers_count: int | None
    url: str


class TopicListResponse(BaseModel):
    """Response containing a list of topics."""

    topics: list[Topic]


# --- Analysis models ---


class AnalysisStartRequest(BaseModel):
    """Request to start analysis for a topic."""

    topic_id: int


class AnalysisStartResponse(BaseModel):
    """Response after starting an analysis task."""

    task_id: UUID
    status: str


class AnalysisStatusResponse(BaseModel):
    """Response with current analysis task status."""

    task_id: UUID
    status: str
    progress_percent: int
    current_stage: str | None
    total_chunks: int | None
    processed_chunks: int | None
    error_message: str | None
    report_id: int | None


# --- Report models ---


class Report(BaseModel):
    """A complete analysis report."""

    id: int
    topic_id: int
    hot_topics: list[HotTopic]
    user_problems: list[UserProblem]
    trending_discussions: list[TrendingDiscussion]
    generated_at: datetime


class ReportListResponse(BaseModel):
    """Response containing a list of reports."""

    reports: list[Report]


# --- Internal models ---


class Chunk(BaseModel):
    """A chunk of post data for Gemini API analysis."""

    index: int
    posts_data: list[dict]
    estimated_tokens: int


class PartialResult(BaseModel):
    """Result of analyzing a single chunk."""

    chunk_index: int
    topics_found: list[HotTopic]
    user_problems: list[UserProblem]
    active_discussions: list[TrendingDiscussion]
