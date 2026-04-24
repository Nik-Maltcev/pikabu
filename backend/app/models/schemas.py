"""Pydantic models for API request/response and internal data structures."""

from __future__ import annotations

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


# --- Niche search sub-models ---


class KeyPain(BaseModel):
    """A key user pain point with frequency and emotional charge."""

    description: str
    frequency: str  # "Массово" / "Часто" / "Периодически" / "Редко, но метко"
    emotional_charge: str  # "Высокий" / "Средний"
    examples: list[str] = []


class JTBDAnalysis(BaseModel):
    """Jobs To Be Done analysis for a specific pain point."""

    pain_description: str
    situational: str
    functional: str
    emotional: str
    current_solution: str


class BusinessIdea(BaseModel):
    """A concrete business idea with MVP plan."""

    name: str
    description: str
    mvp_plan: str


class MarketTrend(BaseModel):
    """A market or technology trend amplifying the problem."""

    name: str
    description: str
    monetization_hint: str


class NicheReport(BaseModel):
    """Full niche search report."""

    key_pains: list[KeyPain] = []
    jtbd_analyses: list[JTBDAnalysis] = []
    business_ideas: list[BusinessIdea] = []
    market_trends: list[MarketTrend] = []


class NichePartialResult(BaseModel):
    """Result of analyzing a single chunk in niche_search mode."""

    chunk_index: int
    key_pains: list[KeyPain] = []
    jtbd_analyses: list[JTBDAnalysis] = []


# --- Topic models ---


class Topic(BaseModel):
    """A Pikabu topic (community/tag)."""

    id: int
    pikabu_id: str
    name: str
    subscribers_count: int | None
    url: str
    source: str = "pikabu"


class TopicListResponse(BaseModel):
    """Response containing a list of topics."""

    topics: list[Topic]


# --- Analysis models ---


class AnalysisStartRequest(BaseModel):
    """Request to start analysis for a topic."""

    topic_id: int
    days: int = 30  # 7, 14, or 30
    source: str = "pikabu"
    analysis_mode: str = "topic_analysis"  # "topic_analysis" or "niche_search"
    habr_topic_id: int | None = None
    vcru_topic_id: int | None = None


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
    analysis_mode: str = "topic_analysis"


# --- Report models ---


class Report(BaseModel):
    """A complete analysis report."""

    id: int
    topic_id: int
    hot_topics: list[HotTopic]
    user_problems: list[UserProblem]
    trending_discussions: list[TrendingDiscussion]
    generated_at: datetime
    sources: str = "pikabu"
    analysis_mode: str = "topic_analysis"
    niche_data: NicheReport | None = None


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


# --- MiroFish export models ---


class MirofishExportRequest(BaseModel):
    """Request to export parsed data to MiroFish."""

    topic_id: int
    mirofish_url: str = "http://localhost:5001"
    simulation_requirement: str
    project_name: str | None = None
    source: str | None = None
    habr_topic_id: int | None = None
    vcru_topic_id: int | None = None


class MirofishExportResponse(BaseModel):
    """Response after exporting data to MiroFish."""

    success: bool
    mirofish_project_id: str | None = None
    posts_count: int = 0
    comments_count: int = 0
    message: str = ""
    error: str | None = None
