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
from app.config import settings
from app.models.database import AnalysisTask, Report as DBReport, Topic as DBTopic
from app.models.schemas import (
    AnalysisStartRequest,
    AnalysisStartResponse,
    AnalysisStatusResponse,
    MirofishExportRequest,
    MirofishExportResponse,
    NicheReport,
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
        source=t.source,
    )


def _report_to_schema(r: DBReport) -> Report:
    """Convert a DB Report to a Pydantic Report schema."""
    niche = None
    if r.analysis_mode == "niche_search" and r.niche_data:
        niche = NicheReport(**r.niche_data) if isinstance(r.niche_data, dict) else r.niche_data
    return Report(
        id=r.id,
        topic_id=r.topic_id,
        hot_topics=r.hot_topics or [],
        user_problems=r.user_problems or [],
        trending_discussions=r.trending_discussions or [],
        generated_at=r.generated_at,
        sources=r.sources,
        analysis_mode=r.analysis_mode or "topic_analysis",
        niche_data=niche,
    )


@router.get("/topics", response_model=TopicListResponse)
async def get_topics(
    search: str = Query(default="", description="Filter topics by name substring"),
    source: str = Query(default="pikabu", description="Source filter: pikabu, habr, vcru, both, or all"),
    session: AsyncSession = Depends(get_session),
) -> TopicListResponse:
    """Return the list of available topics, optionally filtered by search and source."""
    try:
        tm = TopicManager(session)
        topics = await tm.fetch_topics(source=source)
        if search:
            topics = TopicManager.filter_topics(topics, search)
        return TopicListResponse(topics=[_topic_to_schema(t) for t in topics])
    except Exception as exc:
        logger.exception("Error fetching topics: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/parse/start")
async def start_parse_only(
    topic_id: int = Query(...),
    days: int = Query(default=30),
    source: str = Query(default="pikabu"),
    session: AsyncSession = Depends(get_session),
):
    """Parse-only: collect posts without LLM analysis.

    Used by MiroFish to get fresh raw data without wasting LLM tokens.
    Returns immediately, parsing runs in background.
    """
    import asyncio
    from app.models.database import AnalysisTask

    # Validate topic
    result = await session.execute(
        select(DBTopic).where(DBTopic.id == topic_id)
    )
    topic = result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    if days not in (7, 14, 30):
        raise HTTPException(status_code=400, detail="days must be 7, 14, or 30")

    # Create task
    task = AnalysisTask(topic_id=topic_id, status="pending", progress_percent=0)
    session.add(task)
    await session.flush()
    task_id = task.id

    asyncio.create_task(
        _run_parse_only_background(topic_id, task_id, days, source)
    )

    await session.commit()
    return {"task_id": str(task_id), "status": "pending", "mode": "parse_only"}


async def _run_parse_only_background(
    topic_id: int, task_id, days: int, source: str
):
    """Parse posts only — no LLM analysis."""
    from app.database import async_session
    from app.services.parser import ParserService
    from app.services.habr_parser import HabrParserService
    from app.services.vcru_parser import VcruParserService
    from app.services.pipeline import _update_task

    try:
        async with async_session() as session:
            from app.models.database import AnalysisTask
            result = await session.execute(
                select(AnalysisTask).where(AnalysisTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return

            try:
                await _update_task(session, task, status="parsing", current_stage="Парсинг...", progress_percent=0)
                await session.commit()

                async def _progress(stage: str, percent: int):
                    await _update_task(session, task, current_stage=f"{stage} {percent}%", progress_percent=min(percent, 95))
                    await session.commit()

                if source in ("pikabu",):
                    parser = ParserService(session)
                    await parser.parse_topic(topic_id, callback=_progress, days=days)
                elif source in ("habr",):
                    parser = HabrParserService(session)
                    await parser.parse_topic(topic_id, callback=_progress, days=days)
                elif source in ("vcru",):
                    parser = VcruParserService(session)
                    await parser.parse_topic(topic_id, callback=_progress, days=days)

                await _update_task(session, task, status="completed", current_stage="Парсинг завершён", progress_percent=100)
                await session.commit()

            except Exception as exc:
                logger.error("Parse-only failed for topic %s: %s", topic_id, exc, exc_info=True)
                await _update_task(session, task, status="failed", error_message=str(exc))
                await session.commit()
    except Exception:
        logger.exception("Parse-only background failed for topic %s", topic_id)


@router.post("/analysis/start", response_model=AnalysisStartResponse)
async def start_analysis(
    request: AnalysisStartRequest,
    session: AsyncSession = Depends(get_session),
) -> AnalysisStartResponse:
    """Start a new analysis task for the given topic."""
    # Validate analysis_mode
    if request.analysis_mode not in ("topic_analysis", "niche_search"):
        raise HTTPException(status_code=400, detail="analysis_mode must be 'topic_analysis' or 'niche_search'")

    # Validate: source="both" requires habr_topic_id
    if request.source == "both" and request.habr_topic_id is None:
        raise HTTPException(
            status_code=400,
            detail="habr_topic_id is required when source is 'both'",
        )

    # Validate: source="all" requires habr_topic_id and vcru_topic_id
    if request.source == "all":
        if request.habr_topic_id is None:
            raise HTTPException(
                status_code=400,
                detail="habr_topic_id is required when source is 'all'",
            )
        if request.vcru_topic_id is None:
            raise HTTPException(
                status_code=400,
                detail="vcru_topic_id is required when source is 'all'",
            )

    # Validate topic exists
    result = await session.execute(
        select(DBTopic).where(DBTopic.id == request.topic_id)
    )
    topic = result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Validate habr_topic_id exists if provided
    if request.habr_topic_id is not None:
        habr_result = await session.execute(
            select(DBTopic).where(DBTopic.id == request.habr_topic_id)
        )
        if habr_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Habr topic not found")

    # Validate vcru_topic_id exists if provided
    if request.vcru_topic_id is not None:
        vcru_result = await session.execute(
            select(DBTopic).where(DBTopic.id == request.vcru_topic_id)
        )
        if vcru_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="VC.ru topic not found")

    # Validate days
    if request.days not in (7, 14, 30):
        raise HTTPException(status_code=400, detail="days must be 7, 14, or 30")

    # Check for already running analysis
    try:
        # Create the task record first so we can return its id
        task = AnalysisTask(topic_id=request.topic_id, status="pending", progress_percent=0, analysis_mode=request.analysis_mode)
        session.add(task)
        await session.flush()
        task_id = task.id

        # Launch background analysis (uses its own session)
        asyncio.create_task(
            _run_analysis_background(
                request.topic_id,
                task_id,
                request.days,
                source=request.source,
                analysis_mode=request.analysis_mode,
                habr_topic_id=request.habr_topic_id,
                vcru_topic_id=request.vcru_topic_id,
            )
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
        analysis_mode=task.analysis_mode or "topic_analysis",
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


@router.get("/posts/{topic_id}")
async def get_posts_by_topic(
    topic_id: int,
    days: int = Query(default=0, description="Filter posts by last N days (0 = all)"),
    session: AsyncSession = Depends(get_session),
):
    """Return posts with comments for a topic (for MiroFish integration).

    Args:
        topic_id: Topic ID
        days: Filter by last N days (7, 14, 30). 0 = return all posts.
    """
    from datetime import datetime, timezone, timedelta
    from app.models.database import Post

    # Validate topic exists
    topic_result = await session.execute(
        select(DBTopic).where(DBTopic.id == topic_id)
    )
    topic = topic_result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Load posts with optional date filter
    query = select(Post).where(Post.topic_id == topic_id)
    if days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.where(Post.published_at >= since)

    result = await session.execute(query)
    posts = result.scalars().all()

    posts_data = []
    for post in posts:
        await session.refresh(post, ["comments"])
        posts_data.append({
            "title": post.title,
            "body": post.body or "",
            "published_at": post.published_at.isoformat() if post.published_at else "",
            "rating": post.rating or 0,
            "comments_count": post.comments_count or 0,
            "url": post.url or "",
            "comments": [
                {
                    "body": c.body,
                    "published_at": c.published_at.isoformat() if c.published_at else "",
                    "rating": c.rating or 0,
                }
                for c in post.comments
            ],
        })

    return {
        "topic_id": topic_id,
        "topic_name": topic.name,
        "source": topic.source,
        "posts_count": len(posts_data),
        "posts": posts_data,
    }


@router.post("/export/mirofish", response_model=MirofishExportResponse)
async def export_to_mirofish(
    request: MirofishExportRequest,
    session: AsyncSession = Depends(get_session),
) -> MirofishExportResponse:
    """Export parsed posts to MiroFish for simulation.

    Takes posts from the PIKABU database and sends them to MiroFish API
    which will build a knowledge graph and run multi-agent simulation.
    """
    from app.services.mirofish_sender import MirofishSender, MirofishSendError

    # Validate topic exists
    result = await session.execute(
        select(DBTopic).where(DBTopic.id == request.topic_id)
    )
    topic = result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    if not request.simulation_requirement.strip():
        raise HTTPException(
            status_code=400,
            detail="simulation_requirement is required",
        )

    try:
        sender = MirofishSender(session)
        mirofish_result = await sender.send_topic(
            topic_id=request.topic_id,
            mirofish_url=request.mirofish_url or settings.mirofish_url,
            simulation_requirement=request.simulation_requirement,
            project_name=request.project_name,
            source=request.source,
            habr_topic_id=request.habr_topic_id,
            vcru_topic_id=request.vcru_topic_id,
        )

        data = mirofish_result.get("data", {})
        return MirofishExportResponse(
            success=True,
            mirofish_project_id=data.get("project_id"),
            posts_count=data.get("posts_count", 0),
            comments_count=data.get("comments_count", 0),
            message=f"Данные отправлены в MiroFish. Project: {data.get('project_id', '?')}",
        )

    except MirofishSendError as exc:
        logger.error("MiroFish export failed: %s", exc)
        return MirofishExportResponse(
            success=False,
            error=str(exc),
            message="Ошибка отправки в MiroFish",
        )
    except Exception as exc:
        logger.exception("Unexpected error during MiroFish export: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _run_analysis_background(
    topic_id: int,
    task_id: UUID,
    days: int = 30,
    source: str = "pikabu",
    analysis_mode: str = "topic_analysis",
    habr_topic_id: int | None = None,
    vcru_topic_id: int | None = None,
) -> None:
    """Run the full analysis pipeline in the background.

    Creates its own DB session so the request session can be closed.
    Uses the task already created by the router endpoint.

    Args:
        topic_id: Primary topic ID (pikabu topic or habr topic for source="habr").
        task_id: The analysis task UUID.
        days: Number of days to parse.
        source: "pikabu", "habr", "vcru", "both", or "all".
        analysis_mode: "topic_analysis" or "niche_search".
        habr_topic_id: Habr topic ID (required for "habr", "both", and "all" modes).
        vcru_topic_id: VC.ru topic ID (required for "vcru" and "all" modes).
    """
    from app.database import async_session
    from app.services.analyzer import AnalyzerError, AnalyzerService
    from app.services.cache import CacheService
    from app.services.chunker import chunk_data
    from app.services.parser import ParserError, ParserService
    from app.services.habr_parser import HabrParserError, HabrParserService
    from app.services.vcru_parser import VcruParserError, VcruParserService
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

            analyzer = AnalyzerService()
            partial_results: list[PartialResult] = []

            # Determine sources label for the report
            if source == "both":
                sources_label = "pikabu,habr"
            elif source == "all":
                sources_label = "pikabu,habr,vcru"
            elif source == "vcru":
                sources_label = "vcru"
            else:
                sources_label = source

            try:
                # Phase 1: Parsing (0% → 50%)
                if source in ("pikabu", "both", "all"):
                    parser = ParserService(session)
                    stage_label = "Загрузка постов с Pikabu..."
                    await _update_task(session, task, status="parsing", current_stage=stage_label, progress_percent=0)
                    await session.commit()

                    async def _pikabu_progress(stage: str, percent: int) -> None:
                        if source == "both":
                            overall = int(percent * 0.25)  # 0-25% for pikabu in "both" mode
                        elif source == "all":
                            overall = int(percent * 0.17)  # 0-17% for pikabu in "all" mode
                        else:
                            overall = int(percent * 0.5)
                        post_info = f"Загрузка постов с Pikabu... {percent}%"
                        await _update_task(session, task, current_stage=post_info, progress_percent=overall)
                        await session.commit()

                    await parser.parse_topic(topic_id, callback=_pikabu_progress, days=days)

                if source in ("habr", "both", "all"):
                    habr_parser = HabrParserService(session)
                    habr_tid = habr_topic_id if habr_topic_id is not None else topic_id
                    stage_label = "Загрузка статей с Habr..."
                    if source == "both":
                        base_progress = 25
                    elif source == "all":
                        base_progress = 17
                    else:
                        base_progress = 0
                    await _update_task(session, task, status="parsing", current_stage=stage_label, progress_percent=base_progress)
                    await session.commit()

                    async def _habr_progress(stage: str, percent: int) -> None:
                        if source == "both":
                            overall = 25 + int(percent * 0.25)  # 25-50% for habr in "both" mode
                        elif source == "all":
                            overall = 17 + int(percent * 0.17)  # 17-34% for habr in "all" mode
                        else:
                            overall = int(percent * 0.5)
                        post_info = f"Загрузка статей с Habr... {percent}%"
                        await _update_task(session, task, current_stage=post_info, progress_percent=overall)
                        await session.commit()

                    await habr_parser.parse_topic(habr_tid, callback=_habr_progress, days=days)

                if source in ("vcru", "all"):
                    vcru_parser = VcruParserService(session)
                    vcru_tid = vcru_topic_id if vcru_topic_id is not None else topic_id
                    stage_label = "Загрузка статей с VC.ru..."
                    if source == "all":
                        base_progress = 34
                    else:
                        base_progress = 0
                    await _update_task(session, task, status="parsing", current_stage=stage_label, progress_percent=base_progress)
                    await session.commit()

                    async def _vcru_progress(stage: str, percent: int) -> None:
                        if source == "all":
                            overall = 34 + int(percent * 0.16)  # 34-50% for vcru in "all" mode
                        else:
                            overall = int(percent * 0.5)
                        post_info = f"Загрузка статей с VC.ru... {percent}%"
                        await _update_task(session, task, current_stage=post_info, progress_percent=overall)
                        await session.commit()

                    await vcru_parser.parse_topic(vcru_tid, callback=_vcru_progress, days=days)

                # Phase 2: Chunking + Analysis (50% → 85%)
                await _update_task(session, task, status="chunk_analysis", current_stage="Подготовка данных для анализа...", progress_percent=50)
                await session.commit()

                # Load posts from all relevant topic_ids
                posts_data = await _load_posts_as_dicts(session, topic_id)
                if source == "both" and habr_topic_id is not None and habr_topic_id != topic_id:
                    habr_posts = await _load_posts_as_dicts(session, habr_topic_id)
                    posts_data.extend(habr_posts)
                if source == "all":
                    if habr_topic_id is not None and habr_topic_id != topic_id:
                        habr_posts = await _load_posts_as_dicts(session, habr_topic_id)
                        posts_data.extend(habr_posts)
                    if vcru_topic_id is not None and vcru_topic_id != topic_id:
                        vcru_posts = await _load_posts_as_dicts(session, vcru_topic_id)
                        posts_data.extend(vcru_posts)

                chunks = chunk_data(posts_data, max_tokens=settings.llm_chunk_size)
                total_chunks = len(chunks)
                logger.info("Topic %s (source=%s): %d posts, %d chunks", topic_id, source, len(posts_data), total_chunks)
                for c in chunks:
                    logger.info("  Chunk %d: %d posts, ~%d tokens", c.index, len(c.posts_data), c.estimated_tokens)
                await _update_task(session, task, total_chunks=total_chunks, processed_chunks=0)
                await session.commit()

                # Analyze each chunk
                for i, chunk in enumerate(chunks):
                    pr = await analyzer.analyze_chunk(chunk, analysis_mode=analysis_mode)
                    partial_results.append(pr)
                    _save_partial_result_to_db(session, task.id, pr)
                    await session.commit()

                    processed = i + 1
                    chunk_progress = 50 + int((processed / max(total_chunks, 1)) * 35)
                    await _update_task(
                        session, task,
                        processed_chunks=processed,
                        progress_percent=min(chunk_progress, 85),
                        current_stage=f"AI-анализ: чанк {processed} из {total_chunks}...",
                    )
                    await session.commit()

                    if processed < total_chunks:
                        await asyncio.sleep(5)

                # Phase 3: Aggregation (85% → 100%)
                await _update_task(session, task, status="aggregating", current_stage="Формирование итогового отчёта...", progress_percent=85)
                await session.commit()

                report_data = await analyzer.hierarchical_aggregate(partial_results, analysis_mode=analysis_mode)

                # Save report with sources
                from datetime import datetime, timezone

                if analysis_mode == "niche_search":
                    niche_data = {
                        "key_pains": [p.model_dump() if hasattr(p, "model_dump") else p for p in report_data.get("key_pains", [])],
                        "jtbd_analyses": [j.model_dump() if hasattr(j, "model_dump") else j for j in report_data.get("jtbd_analyses", [])],
                        "business_ideas": [b.model_dump() if hasattr(b, "model_dump") else b for b in report_data.get("business_ideas", [])],
                        "market_trends": [m.model_dump() if hasattr(m, "model_dump") else m for m in report_data.get("market_trends", [])],
                    }
                    db_report = DBReport(
                        topic_id=topic_id,
                        task_id=task.id,
                        hot_topics=[],
                        user_problems=[],
                        trending_discussions=[],
                        niche_data=niche_data,
                        analysis_mode="niche_search",
                        generated_at=datetime.now(timezone.utc),
                        sources=sources_label,
                    )
                else:
                    hot_topics = report_data.get("hot_topics", [])
                    user_problems = report_data.get("user_problems", [])
                    trending = report_data.get("trending_discussions", [])

                    db_report = DBReport(
                        topic_id=topic_id,
                        task_id=task.id,
                        hot_topics=[t.model_dump() if hasattr(t, "model_dump") else t for t in hot_topics],
                        user_problems=[p.model_dump() if hasattr(p, "model_dump") else p for p in user_problems],
                        trending_discussions=[d.model_dump() if hasattr(d, "model_dump") else d for d in trending],
                        analysis_mode="topic_analysis",
                        generated_at=datetime.now(timezone.utc),
                        sources=sources_label,
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
