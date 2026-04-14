"""Pipeline service — orchestrates the full analysis pipeline.

Flow: cache check → parse (if needed) → chunk → analyze chunks → aggregate → save report.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AnalysisTask, PartialResult as DBPartialResult, Post, Report as DBReport
from app.models.schemas import Chunk, HotTopic, PartialResult, TrendingDiscussion, UserProblem
from app.services.analyzer import AnalyzerError, AnalyzerService
from app.services.cache import CacheService
from app.services.chunker import chunk_data
from app.services.parser import ParserError, ParserService

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {"pending", "parsing", "chunk_analysis", "aggregating"}


class PipelineError(Exception):
    """Raised when the pipeline encounters an unrecoverable error."""


class AnalysisAlreadyRunningError(PipelineError):
    """Raised when an analysis task is already active for the topic."""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"Analysis already running for this topic: task_id={task_id}")


async def _get_active_task(session: AsyncSession, topic_id: int) -> AnalysisTask | None:
    """Return an active analysis task for the topic, or None."""
    result = await session.execute(
        select(AnalysisTask).where(
            AnalysisTask.topic_id == topic_id,
            AnalysisTask.status.in_(ACTIVE_STATUSES),
        )
    )
    return result.scalar_one_or_none()


async def _update_task(
    session: AsyncSession,
    task: AnalysisTask,
    *,
    status: str | None = None,
    current_stage: str | None = None,
    progress_percent: int | None = None,
    processed_chunks: int | None = None,
    total_chunks: int | None = None,
    error_message: str | None = None,
    report_id: int | None = None,
) -> None:
    """Update task fields and flush to DB."""
    if status is not None:
        task.status = status
    if current_stage is not None:
        task.current_stage = current_stage
    if progress_percent is not None:
        task.progress_percent = progress_percent
    if processed_chunks is not None:
        task.processed_chunks = processed_chunks
    if total_chunks is not None:
        task.total_chunks = total_chunks
    if error_message is not None:
        task.error_message = error_message
    if report_id is not None:
        # Store report_id in the relationship via the reports list
        pass
    task.updated_at = datetime.now(timezone.utc)
    await session.flush()


async def _load_posts_as_dicts(session: AsyncSession, topic_id: int) -> list[dict]:
    """Load all posts (with comments) for a topic as plain dicts for chunking."""
    result = await session.execute(
        select(Post).where(Post.topic_id == topic_id)
    )
    posts = result.scalars().all()

    posts_data: list[dict] = []
    for post in posts:
        # Eagerly load comments
        await session.refresh(post, ["comments"])
        post_dict = {
            "pikabu_post_id": post.pikabu_post_id,
            "title": post.title,
            "body": post.body or "",
            "published_at": post.published_at.isoformat() if post.published_at else "",
            "rating": post.rating,
            "comments_count": post.comments_count,
            "url": post.url,
            "comments": [
                {
                    "pikabu_comment_id": c.pikabu_comment_id,
                    "body": c.body,
                    "published_at": c.published_at.isoformat() if c.published_at else "",
                    "rating": c.rating,
                }
                for c in post.comments
            ],
        }
        posts_data.append(post_dict)
    return posts_data


def _save_partial_result_to_db(
    session: AsyncSession,
    task_id,
    result: PartialResult,
) -> DBPartialResult:
    """Create a DBPartialResult from a schema PartialResult and add to session."""
    db_pr = DBPartialResult(
        task_id=task_id,
        chunk_index=result.chunk_index,
        topics_found=[t.model_dump() for t in result.topics_found],
        user_problems=[p.model_dump() for p in result.user_problems],
        active_discussions=[d.model_dump() for d in result.active_discussions],
    )
    session.add(db_pr)
    return db_pr


async def run_full_analysis(
    topic_id: int,
    session: AsyncSession,
    *,
    days: int = 30,
    parser_service: ParserService | None = None,
    cache_service: CacheService | None = None,
    analyzer_service: AnalyzerService | None = None,
) -> AnalysisTask:
    """Orchestrate the full analysis pipeline for a topic.

    Steps:
        1. Check for active tasks (block duplicate runs)
        2. Create AnalysisTask with status "pending"
        3. Check cache → parse if needed (status "parsing")
        4. Chunk data (status "chunk_analysis")
        5. Analyze each chunk, saving partial results
        6. Aggregate results (status "aggregating")
        7. Save report (status "completed")

    On error: set status to "failed" with error_message, preserve partial results.

    Args:
        topic_id: DB primary key of the topic.
        session: SQLAlchemy async session.
        parser_service: Optional injected ParserService (for testing).
        cache_service: Optional injected CacheService (for testing).
        analyzer_service: Optional injected AnalyzerService (for testing).

    Returns:
        The AnalysisTask record.

    Raises:
        AnalysisAlreadyRunningError: If an active task exists for this topic.
    """
    # 1. Block duplicate runs
    active = await _get_active_task(session, topic_id)
    if active is not None:
        raise AnalysisAlreadyRunningError(str(active.id))

    # 2. Create task
    task = AnalysisTask(topic_id=topic_id, status="pending", progress_percent=0)
    session.add(task)
    await session.flush()

    # Resolve services
    parser = parser_service or ParserService(session)
    cache = cache_service or CacheService(session)
    analyzer = analyzer_service or AnalyzerService()

    partial_results: list[PartialResult] = []

    try:
        # 3. Cache check → parse if needed
        cache_valid = await cache.is_cache_valid(topic_id)
        if not cache_valid:
            await _update_task(session, task, status="parsing", current_stage="parsing", progress_percent=0)

            async def _parse_progress(stage: str, percent: int) -> None:
                await _update_task(session, task, current_stage=stage, progress_percent=min(percent, 30))

            await parser.parse_topic(topic_id, callback=_parse_progress, days=days)

        # 4. Chunk data
        await _update_task(
            session, task,
            status="chunk_analysis",
            current_stage="chunk_analysis",
            progress_percent=30,
        )

        posts_data = await _load_posts_as_dicts(session, topic_id)
        chunks = chunk_data(posts_data)
        total_chunks = len(chunks)
        await _update_task(session, task, total_chunks=total_chunks, processed_chunks=0)

        # 5. Analyze each chunk
        for i, chunk in enumerate(chunks):
            result = await analyzer.analyze_chunk(chunk)
            partial_results.append(result)

            # Save partial result to DB
            _save_partial_result_to_db(session, task.id, result)
            await session.flush()

            processed = i + 1
            # Progress: 30% (parsing) + 50% (chunk analysis) proportional
            chunk_progress = 30 + int((processed / max(total_chunks, 1)) * 50)
            await _update_task(
                session, task,
                processed_chunks=processed,
                progress_percent=min(chunk_progress, 80),
            )

        # 6. Aggregate
        await _update_task(
            session, task,
            status="aggregating",
            current_stage="aggregating",
            progress_percent=80,
        )

        report_data = await analyzer.hierarchical_aggregate(partial_results)

        # 7. Save report
        hot_topics = report_data.get("hot_topics", [])
        user_problems = report_data.get("user_problems", [])
        trending = report_data.get("trending_discussions", [])

        db_report = DBReport(
            topic_id=topic_id,
            task_id=task.id,
            hot_topics=[t.model_dump() if hasattr(t, "model_dump") else t for t in hot_topics],
            user_problems=[p.model_dump() if hasattr(p, "model_dump") else p for p in user_problems],
            trending_discussions=[d.model_dump() if hasattr(d, "model_dump") else d for d in trending],
            generated_at=datetime.now(timezone.utc),
        )
        session.add(db_report)
        await session.flush()

        await _update_task(
            session, task,
            status="completed",
            current_stage="completed",
            progress_percent=100,
        )

        return task

    except AnalysisAlreadyRunningError:
        raise
    except (AnalyzerError, ParserError, Exception) as exc:
        logger.error("Pipeline failed for topic %s: %s", topic_id, exc, exc_info=True)

        # Save any partial results collected so far
        for pr in partial_results:
            # Check if already saved (avoid duplicates)
            existing = await session.execute(
                select(DBPartialResult).where(
                    DBPartialResult.task_id == task.id,
                    DBPartialResult.chunk_index == pr.chunk_index,
                )
            )
            if existing.scalar_one_or_none() is None:
                _save_partial_result_to_db(session, task.id, pr)

        await _update_task(
            session, task,
            status="failed",
            current_stage="failed",
            error_message=str(exc),
        )
        await session.flush()

        return task
