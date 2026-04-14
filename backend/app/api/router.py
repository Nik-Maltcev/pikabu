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
    """
    from app.database import async_session

    try:
        async with async_session() as session:
            # Re-load the task we already created
            result = await session.execute(
                select(AnalysisTask).where(AnalysisTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if task is None:
                logger.error("Background task %s not found in DB", task_id)
                return

            await run_full_analysis(topic_id, session, days=days)
            await session.commit()
    except AnalysisAlreadyRunningError:
        logger.info("Analysis already running for topic %s, skipping", topic_id)
    except Exception:
        logger.exception("Background analysis failed for topic %s", topic_id)
