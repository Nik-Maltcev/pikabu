"""REST API router for Pikabu Topic Analyzer.

Endpoints:
- GET  /api/topics                         → TopicListResponse
- POST /api/analysis/start                 → AnalysisStartResponse
- GET  /api/analysis/status/{task_id}      → AnalysisStatusResponse
- GET  /api/reports/{topic_id}             → ReportListResponse
- GET  /api/reports/{topic_id}/{report_id} → Report
"""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.database import AnalysisTask, Report as DBReport, Topic as DBTopic
from app.models.schemas import (
    AnalysisStartRequest,
    AnalysisStartResponse,
    AnalysisStatusResponse,
    Report,
    ReportListResponse,
    Topic,
    TopicListResponse,
)
from app.services.pipeline import AnalysisAlreadyRunningError, run_full_analysis
from app.services.topic_manager import TopicManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _topic_to_schema(t: DBTopic) -> Topic:
    """Convert a DB Topic to a Pydantic Topic schema."""
    return Topic(
        id=t.id,
        pikabu_id=t.pikabu_id,
        name=t.name,
        subscribers_count=t.subscribers_count,
        url=t.url,
    )


def _report_to_schema(r: DBReport) -> Report:
    """Convert a DB Report to a Pydantic Report schema."""
    return Report(
        id=r.id,
        topic_id=r.topic_id,
        hot_topics=r.hot_topics or [],
        user_problems=r.user_problems or [],
        trending_discussions=r.trending_discussions or [],
        generated_at=r.generated_at,
    )


@router.get("/topics", response_model=TopicListResponse)
async def get_topics(
    search: str = Query(default="", description="Filter topics by name substring"),
    session: AsyncSession = Depends(get_session),
) -> TopicListResponse:
    """Return the list of available Pikabu topics, optionally filtered by search."""
    try:
        tm = TopicManager(session)
        topics = await tm.fetch_topics()
        if search:
            topics = TopicManager.filter_topics(topics, search)
        return TopicListResponse(topics=[_topic_to_schema(t) for t in topics])
    except Exception as exc:
        logger.exception("Error fetching topics: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/analysis/start", response_model=AnalysisStartResponse)
async def start_analysis(
    request: AnalysisStartRequest,
    session: AsyncSession = Depends(get_session),
) -> AnalysisStartResponse:
    """Start a new analysis task for the given topic."""
    # Validate topic exists
    result = await session.execute(
        select(DBTopic).where(DBTopic.id == request.topic_id)
    )
    topic = result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Validate days
    if request.days not in (7, 14, 30):
        raise HTTPException(status_code=400, detail="days must be 7, 14, or 30")

    # Check for already running analysis
    try:
        # Create the task record first so we can return its id
        task = AnalysisTask(topic_id=request.topic_id, status="pending", progress_percent=0)
        session.add(task)
        await session.flush()
        task_id = task.id

        # Launch background analysis (uses its own session)
        asyncio.create_task(
            _run_analysis_background(request.topic_id, task_id, request.days)
        )

        await session.commit()
        return AnalysisStartResponse(task_id=task_id, status="pending")

    except AnalysisAlreadyRunningError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Analysis already running for this topic: task_id={exc.task_id}",
        ) from exc


@router.get("/analysis/status/{task_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AnalysisStatusResponse:
    """Return the current status of an analysis task."""
    result = await session.execute(
        select(AnalysisTask).where(AnalysisTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Find report_id if task is completed
    report_id = None
    if task.status == "completed":
        report_result = await session.execute(
            select(DBReport.id).where(DBReport.task_id == task.id)
        )
        report_id = report_result.scalar_one_or_none()

    return AnalysisStatusResponse(
        task_id=task.id,
        status=task.status,
        progress_percent=task.progress_percent,
        current_stage=task.current_stage,
        total_chunks=task.total_chunks,
        processed_chunks=task.processed_chunks,
        error_message=task.error_message,
        report_id=report_id,
    )


@router.get("/reports/{topic_id}", response_model=ReportListResponse)
async def get_reports(
    topic_id: int,
    session: AsyncSession = Depends(get_session),
) -> ReportListResponse:
    """Return all reports for a given topic."""
    # Validate topic exists
    topic_result = await session.execute(
        select(DBTopic).where(DBTopic.id == topic_id)
    )
    if topic_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    result = await session.execute(
        select(DBReport)
        .where(DBReport.topic_id == topic_id)
        .order_by(DBReport.generated_at.desc())
    )
    reports = result.scalars().all()
    return ReportListResponse(reports=[_report_to_schema(r) for r in reports])


@router.get("/reports/{topic_id}/{report_id}", response_model=Report)
async def get_report(
    topic_id: int,
    report_id: int,
    session: AsyncSession = Depends(get_session),
) -> Report:
    """Return a specific report."""
    result = await session.execute(
        select(DBReport).where(
            DBReport.id == report_id,
            DBReport.topic_id == topic_id,
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_to_schema(report)


async def _run_analysis_background(topic_id: int, task_id: UUID, days: int = 30) -> None:
    """Run the full analysis pipeline in the background.

    Creates its own DB session so the request session can be closed.
    Uses the task already created by the router endpoint.
    """
    from app.database import async_session
    from app.services.analyzer import AnalyzerError, AnalyzerService
    from app.services.cache import CacheService
    from app.services.chunker import chunk_data
    from app.services.parser import ParserError, ParserService
    from app.models.database import PartialResult as DBPartialResult, Post, Report as DBReport
    from app.models.schemas import PartialResult
    from app.services.pipeline import _update_task, _load_posts_as_dicts, _save_partial_result_to_db

    try:
        async with async_session() as session:
            result = await session.execute(
                select(AnalysisTask).where(AnalysisTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if task is None:
                logger.error("Background task %s not found in DB", task_id)
                return

            parser = ParserService(session)
            cache = CacheService(session)
            analyzer = AnalyzerService()
            partial_results: list[PartialResult] = []

            try:
                # Phase 1: Parsing (0% → 50%)
                await _update_task(session, task, status="parsing", current_stage="Загрузка постов с Pikabu...", progress_percent=0)
                await session.commit()

                async def _parse_progress(stage: str, percent: int) -> None:
                    # Map 0-100% parsing progress to 0-50% overall
                    overall = int(percent * 0.5)
                    post_info = f"Загрузка постов и комментариев... {percent}%"
                    await _update_task(session, task, current_stage=post_info, progress_percent=overall)
                    await session.commit()

                await parser.parse_topic(topic_id, callback=_parse_progress, days=days)

                # Phase 2: Chunking + Analysis (50% → 85%)
                await _update_task(session, task, status="chunk_analysis", current_stage="Подготовка данных для анализа...", progress_percent=50)
                await session.commit()

                posts_data = await _load_posts_as_dicts(session, topic_id)
                chunks = chunk_data(posts_data)
                total_chunks = len(chunks)
                logger.info("Topic %s: %d posts, %d chunks", topic_id, len(posts_data), total_chunks)
                for c in chunks:
                    logger.info("  Chunk %d: %d posts, ~%d tokens", c.index, len(c.posts_data), c.estimated_tokens)
                await _update_task(session, task, total_chunks=total_chunks, processed_chunks=0)
                await session.commit()

                # Analyze each chunk
                for i, chunk in enumerate(chunks):
                    pr = await analyzer.analyze_chunk(chunk)
                    partial_results.append(pr)
                    _save_partial_result_to_db(session, task.id, pr)
                    await session.commit()

                    processed = i + 1
                    # Map chunk progress to 50-85% overall
                    chunk_progress = 50 + int((processed / max(total_chunks, 1)) * 35)
                    await _update_task(
                        session, task,
                        processed_chunks=processed,
                        progress_percent=min(chunk_progress, 85),
                        current_stage=f"AI-анализ: чанк {processed} из {total_chunks}...",
                    )
                    await session.commit()

                    # Pause between LLM calls to avoid rate limits
                    if processed < total_chunks:
                        await asyncio.sleep(5)

                # Phase 3: Aggregation (85% → 100%)
                await _update_task(session, task, status="aggregating", current_stage="Формирование итогового отчёта...", progress_percent=85)
                await session.commit()

                report_data = await analyzer.hierarchical_aggregate(partial_results)

                # Save report
                from datetime import datetime, timezone
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
                await session.commit()

                await _update_task(session, task, status="completed", current_stage="Анализ завершён!", progress_percent=100)
                await session.commit()

            except Exception as exc:
                logger.error("Pipeline failed for topic %s: %s", topic_id, exc, exc_info=True)
                await _update_task(session, task, status="failed", current_stage="Ошибка", error_message=str(exc))
                await session.commit()

    except Exception:
        logger.exception("Background analysis failed for topic %s", topic_id)
