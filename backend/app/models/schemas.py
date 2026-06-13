"""Pydantic models for API request/response and internal data structures."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator


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


class Risk(BaseModel):
    """A structured risk assessment for a business idea."""

    category: str  # "Market Risk" | "Product Risk" | "Customer Risk" | "Execution Risk" | "Financial Risk"
    description: str  # 1-3 sentences specific to the idea
    mitigation: str  # 1-2 sentences actionable step


class Analogue(BaseModel):
    """An analogous business found via competitor lookup."""

    company_name: str
    description: str  # max 200 chars
    annual_revenue: str | None = None  # e.g., "$2M/год" or "~150 млн ₽/год"
    investment_round: str | None = None  # e.g., "Series A — $5M"
    has_ru_competitor: bool | None = None  # competitors exist in Russia


class KeyPain(BaseModel):
    """A key user pain point with frequency and emotional charge."""

    description: str
    frequency: str  # "Массово" / "Часто" / "Периодически" / "Редко, но метко"
    emotional_charge: str  # "Высокий" / "Средний"
    mentions_count: int = 0  # Approximate number of posts/comments mentioning this pain
    examples: list[str] = []


class JTBDAnalysis(BaseModel):
    """Jobs To Be Done analysis for a specific pain point."""

    pain_description: str
    situational: str
    functional: str
    emotional: str
    current_solution: str


class BusinessIdea(BaseModel):
    """A concrete business idea with full analysis."""

    name: str
    description: str
    mvp_plan: str
    demand_level: str = ""  # "Высокий" / "Средний" / "Низкий" — shown free
    competition_level: str = ""  # "Высокая" / "Средняя" / "Низкая" — shown free
    launch_recommendations: list[str] = []  # paid
    risks: list[Risk] = []  # paid — validator handles backward compat with old str format
    positioning: str = ""  # paid
    search_queries: list[str] = []  # paid
    entry_difficulty: str = ""  # "Легко" / "Средне" / "Сложно" — paid
    analogues: list[Analogue] = []  # NEW: analogous businesses

    @field_validator("risks", mode="before")
    @classmethod
    def _coerce_risks(cls, v: list) -> list:
        """Support backward compatibility: convert plain strings to Risk objects."""
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(Risk(category="Execution Risk", description=item, mitigation=""))
            elif isinstance(item, dict):
                # Already a Risk dict — pass through for Pydantic to validate
                result.append(item)
            else:
                # Already a Risk instance or something Pydantic can handle
                result.append(item)
        return result


class MarketTrend(BaseModel):
    """A market or technology trend amplifying the problem."""

    name: str
    description: str
    monetization_hint: str
    market_volume_estimate: str | None = None  # e.g., "~2.5 млрд ₽"
    growth_rate_percent: float | None = None  # YoY real growth after inflation
    data_source_label: str | None = None  # "Оценка ИИ (реальные данные недоступны)" or None


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


# --- Category suggest models ---


class CategorySuggestion(BaseModel):
    """Рекомендация категории от LLM."""

    topic_id: int
    name: str
    reason: str  # Обоснование, до 100 символов


class CategorySuggestRequest(BaseModel):
    """Запрос на подбор категорий."""

    query: str

    @field_validator("query")
    @classmethod
    def validate_query_length(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Минимум 2 символа")
        if len(v) > 200:
            raise ValueError("Максимум 200 символов")
        return v


class CategorySuggestResponse(BaseModel):
    """Ответ с рекомендациями."""

    suggestions: list[CategorySuggestion]
    message: str = ""


# --- Analysis models ---


class AnalysisStartRequest(BaseModel):
    """Request to start analysis for a topic.

    The backend automatically finds duplicate category names across all
    platforms (Pikabu, Habr, VC.ru) and parses them all.
    
    Two modes:
    1. Authenticated user (has token) - report linked to account
    2. Guest (no token) - must provide contact_type + contact_value for notification
       OR can choose to wait on page (wait_on_page=True)
    
    Topic selection: exactly one of topic_id or topic_ids must be provided.
    - topic_id: single category (backward compatible)
    - topic_ids: multiple categories, 1-5 items
    """

    topic_id: int | None = None  # backward compat: одна категория
    topic_ids: list[int] | None = None  # новое: несколько категорий (1-5)
    days: int = 14  # 14 or 30 (30 is paid only)
    analysis_mode: str = "niche_search"  # "niche_search" or "topic_analysis"
    fingerprint: str = ""  # Browser fingerprint for rate limiting
    contact_type: str = ""  # "email" or "telegram" - for notification when ready
    contact_value: str = ""  # email address or telegram username
    wait_on_page: bool = False  # If True, user will wait on page (no contact needed)

    @model_validator(mode="after")
    def validate_topic_selection(self) -> "AnalysisStartRequest":
        if self.topic_id is None and not self.topic_ids:
            raise ValueError("Укажите topic_id или topic_ids")
        if self.topic_id is not None and self.topic_ids:
            raise ValueError("Укажите только topic_id или topic_ids, не оба")
        if self.topic_ids and len(self.topic_ids) > 5:
            raise ValueError("Максимум 5 категорий")
        return self


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
    contact_type: str | None = None
    contact_value: str | None = None


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
    posts_count: int = 0
    comments_count: int = 0


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
