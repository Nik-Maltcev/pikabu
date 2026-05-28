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
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.config import settings
from app.models.database import AnalysisTask, DeviceLimit, Report as DBReport, Topic as DBTopic
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
from app.services.task_queue import analysis_queue

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
    session: AsyncSession = Depends(get_session),
) -> TopicListResponse:
    """Return the unified list of all topics from all platforms, optionally filtered by search."""
    try:
        tm = TopicManager(session)
        topics = await tm.fetch_topics(source="all")
        if search:
            topics = TopicManager.filter_topics(topics, search)
        return TopicListResponse(topics=[_topic_to_schema(t) for t in topics])
    except Exception as exc:
        logger.exception("Error fetching topics: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/limit/check")
async def check_limit(
    fingerprint: str = Query(..., description="Browser fingerprint"),
    session: AsyncSession = Depends(get_session),
):
    """Check how many free analyses remain for this device."""
    FREE_ANALYSIS_LIMIT = 3

    result = await session.execute(
        select(DeviceLimit).where(DeviceLimit.fingerprint == fingerprint)
    )
    device = result.scalar_one_or_none()

    used = device.analyses_count if device else 0
    remaining = max(0, FREE_ANALYSIS_LIMIT - used)

    return {
        "used": used,
        "remaining": remaining,
        "limit": FREE_ANALYSIS_LIMIT,
    }


@router.post("/parse/start")
async def start_parse_only(
    topic_id: int = Query(...),
    days: int = Query(default=30),
    session: AsyncSession = Depends(get_session),
):
    """Parse-only: collect posts without LLM analysis.

    Automatically finds duplicate category names across all platforms
    and parses them all. Used by MiroFish to get fresh raw data.
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

    if days not in (14, 30):
        raise HTTPException(status_code=400, detail="days must be 14 or 30")    # Find all duplicate topics by name across platforms
    tm = TopicManager(session)
    all_topics = await tm.find_duplicates_by_name(topic_id)
    topic_ids_by_source: dict[str, int] = {}
    for t in all_topics:
        topic_ids_by_source[t.source] = t.id

    # Create task
    task = AnalysisTask(topic_id=topic_id, status="pending", progress_percent=0)
    session.add(task)
    await session.flush()
    task_id = task.id

    asyncio.create_task(
        _run_parse_only_background(topic_ids_by_source, task_id, days)
    )

    await session.commit()
    return {"task_id": str(task_id), "status": "pending", "mode": "parse_only"}


async def _run_parse_only_background(
    topic_ids_by_source: dict[str, int], task_id, days: int
):
    """Parse posts only — no LLM analysis. Parses all matched platforms."""
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

                source_list = sorted(topic_ids_by_source.keys())
                num_sources = len(source_list)

                for idx, src in enumerate(source_list):
                    tid = topic_ids_by_source[src]
                    base_pct = int(idx * 95 / max(num_sources, 1))

                    async def _progress(stage: str, percent: int, _base=base_pct, _share=95.0/max(num_sources,1)):
                        overall = _base + int(percent * _share / 100)
                        await _update_task(session, task, current_stage="Сбор данных...", progress_percent=min(overall, 95))
                        await session.commit()

                    if src == "pikabu":
                        parser = ParserService(session)
                    elif src == "habr":
                        parser = HabrParserService(session)
                    elif src == "vcru":
                        parser = VcruParserService(session)
                    else:
                        continue

                    await parser.parse_topic(tid, callback=_progress, days=days)

                await _update_task(session, task, status="completed", current_stage="Парсинг завершён", progress_percent=100)
                await session.commit()

            except Exception as exc:
                logger.error("Parse-only failed: %s", exc, exc_info=True)
                await _update_task(session, task, status="failed", error_message=str(exc))
                await session.commit()
    except Exception:
        logger.exception("Parse-only background failed")


@router.post("/analysis/start", response_model=AnalysisStartResponse)
async def start_analysis(
    request: AnalysisStartRequest,
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(get_session),
) -> AnalysisStartResponse:
    """Start a new analysis task for the given topic.

    Automatically finds duplicate category names across all platforms
    and parses them all together.
    
    Two modes:
    1. Authenticated user (has valid token) - report linked to account
    2. Guest - must provide contact OR wait_on_page=True
    """
    from app.api.auth import get_current_user
    
    FREE_ANALYSIS_LIMIT = 3

    # Validate analysis_mode
    if request.analysis_mode not in ("topic_analysis", "niche_search"):
        raise HTTPException(status_code=400, detail="analysis_mode must be 'topic_analysis' or 'niche_search'")

    # Check if user is authenticated
    user = await get_current_user(authorization, session)
    user_id = user.id if user else None
    
    # Validate contact info (required for guests unless wait_on_page)
    contact_type = request.contact_type.strip() if request.contact_type else ""
    contact_value = request.contact_value.strip() if request.contact_value else ""
    
    if not user and not request.wait_on_page:
        # Guest must provide contact info
        if not contact_type or not contact_value:
            raise HTTPException(
                status_code=400, 
                detail="Укажите контакт для уведомления или выберите 'подождать на странице'"
            )
    
    if contact_type and contact_type not in ("email", "telegram"):
        raise HTTPException(status_code=400, detail="contact_type must be 'email' or 'telegram'")
    
    # Basic validation for contact value
    if contact_type == "email" and contact_value:
        if "@" not in contact_value or "." not in contact_value:
            raise HTTPException(status_code=400, detail="Invalid email format")
    elif contact_type == "telegram" and contact_value:
        # Remove @ prefix if present, store without it
        contact_value = contact_value.lstrip("@")
        if len(contact_value) < 3:
            raise HTTPException(status_code=400, detail="Invalid telegram username")

    # Rate limiting by browser fingerprint
    if request.fingerprint:
        result_limit = await session.execute(
            select(DeviceLimit).where(DeviceLimit.fingerprint == request.fingerprint)
        )
        device = result_limit.scalar_one_or_none()

        if device and device.analyses_count >= FREE_ANALYSIS_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Лимит бесплатных анализов исчерпан. Оплатите для продолжения.",
            )
    else:
        # No fingerprint provided — allow but log warning
        logger.warning("Analysis request without fingerprint — rate limiting skipped")

    # Validate topic exists
    result = await session.execute(
        select(DBTopic).where(DBTopic.id == request.topic_id)
    )
    topic = result.scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Validate days
    if request.days not in (14, 30):
        raise HTTPException(status_code=400, detail="days must be 14 or 30")

    # Find all duplicate topics by name across platforms
    tm = TopicManager(session)
    all_topics = await tm.find_duplicates_by_name(request.topic_id)
    # Build a list of topic IDs grouped by source
    topic_ids_by_source: dict[str, int] = {}
    for t in all_topics:
        topic_ids_by_source[t.source] = t.id

    # Determine source label
    sources = sorted(topic_ids_by_source.keys())
    sources_label = ",".join(sources)

    try:
        # Create the task record with contact info
        task = AnalysisTask(
            topic_id=request.topic_id,
            status="queued",
            progress_percent=0,
            analysis_mode=request.analysis_mode,
            contact_type=contact_type or None,
            contact_value=contact_value or None,
            user_id=user_id,
        )
        session.add(task)
        await session.flush()
        task_id = task.id

        # Add to queue instead of running immediately
        # This prevents overloading LLM APIs when multiple users start analyses
        def make_coro():
            return _run_analysis_background(
                primary_topic_id=request.topic_id,
                topic_ids_by_source=topic_ids_by_source,
                task_id=task_id,
                days=request.days,
                analysis_mode=request.analysis_mode,
                sources_label=sources_label,
            )
        
        queue_position = await analysis_queue.enqueue(task_id, request.topic_id, make_coro)
        logger.info("Task %s queued at position %d", task_id, queue_position)

        # Increment fingerprint usage counter
        if request.fingerprint:
            result_limit = await session.execute(
                select(DeviceLimit).where(DeviceLimit.fingerprint == request.fingerprint)
            )
            device = result_limit.scalar_one_or_none()
            now = datetime.now(timezone.utc)
            if device:
                device.analyses_count += 1
                device.last_analysis_at = now
            else:
                device = DeviceLimit(
                    fingerprint=request.fingerprint,
                    analyses_count=1,
                    last_analysis_at=now,
                )
                session.add(device)

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
        contact_type=task.contact_type,
        contact_value=task.contact_value,
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
    primary_topic_id: int,
    topic_ids_by_source: dict[str, int],
    task_id: UUID,
    days: int = 30,
    analysis_mode: str = "topic_analysis",
    sources_label: str = "pikabu",
) -> None:
    """Run the full analysis pipeline in the background.

    Creates its own DB session so the request session can be closed.
    Automatically parses all platforms where a matching category was found.

    NEW BEHAVIOR (pre-parsed data):
    - If posts exist in DB for the topic, uses them directly (fast!)
    - Optionally updates comments incrementally
    - Falls back to full parsing if no data in DB

    Args:
        primary_topic_id: The topic ID the user originally selected.
        topic_ids_by_source: Mapping of source → topic_id for all matched categories.
        task_id: The analysis task UUID.
        days: Number of days to parse.
        analysis_mode: "topic_analysis" or "niche_search".
        sources_label: Comma-separated list of sources for the report.
    """
    logger.info(
        "Background analysis starting: primary_topic=%s, task=%s, sources=%s, mode=%s",
        primary_topic_id, task_id, sources_label, analysis_mode,
    )

    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func
    from app.database import async_session
    from app.services.analyzer import AnalyzerError, AnalyzerService
    from app.services.cache import CacheService
    from app.services.chunker import chunk_data
    from app.services.parser import ParserError, ParserService
    from app.services.habr_parser import HabrParserError, HabrParserService
    from app.services.vcru_parser import VcruParserError, VcruParserService
    from app.services.background_parser import BackgroundParser
    from app.models.database import PartialResult as DBPartialResult, Post, Report as DBReport
    from app.models.schemas import PartialResult
    from app.services.pipeline import _update_task, _load_posts_as_dicts, _save_partial_result_to_db

    source_list = sorted(topic_ids_by_source.keys())
    num_sources = len(source_list)

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

            try:
                # Check if we have pre-parsed data in DB
                # Count ALL posts for these topics (not filtered by date)
                # Date filtering will happen at analysis stage
                total_posts_in_db = 0
                
                for tid in topic_ids_by_source.values():
                    count_result = await session.execute(
                        select(func.count(Post.id))
                        .where(Post.topic_id == tid)
                    )
                    total_posts_in_db += count_result.scalar() or 0

                use_preparsed = total_posts_in_db >= 10  # Use DB if we have at least 10 posts
                logger.info(
                    "Topic %s: found %d posts in DB (use_preparsed=%s)",
                    primary_topic_id, total_posts_in_db, use_preparsed
                )

                if use_preparsed:
                    # FAST PATH: Use pre-parsed data + incremental comment update
                    await _update_task(
                        session, task,
                        status="updating",
                        current_stage="Обновление источников...",
                        progress_percent=5,
                    )
                    await session.commit()

                    # Incremental comment update (optional, can be skipped for speed)
                    bg_parser = BackgroundParser(session)
                    update_share = 40.0 / max(num_sources, 1)
                    
                    for idx, (src, tid) in enumerate(topic_ids_by_source.items()):
                        base_progress = 5 + int(idx * update_share)
                        
                        async def _progress(stage: str, percent: int, title: str, _base=base_progress, _share=update_share):
                            overall = _base + int(percent * _share / 100)
                            await _update_task(
                                session, task,
                                current_stage="Обновление источников...",
                                progress_percent=min(overall, 45),
                            )
                            await session.commit()

                        try:
                            await bg_parser.update_comments_for_topic(tid, days=days, callback=_progress)
                        except Exception as e:
                            logger.warning("Comment update failed for topic %d: %s", tid, e)
                    
                    await session.commit()
                    
                else:
                    # SLOW PATH: Full parsing (no pre-parsed data)
                    parse_share = 50.0 / max(num_sources, 1)

                    for idx, src in enumerate(source_list):
                        tid = topic_ids_by_source[src]
                        base_progress = int(idx * parse_share)

                        if src == "pikabu":
                            parser = ParserService(session)
                            stage_label = "Сбор данных..."
                        elif src == "habr":
                            parser = HabrParserService(session)
                            stage_label = "Сбор данных..."
                        elif src == "vcru":
                            parser = VcruParserService(session)
                            stage_label = "Сбор данных..."
                        else:
                            continue

                        await _update_task(
                            session, task,
                            status="parsing",
                            current_stage=stage_label,
                            progress_percent=base_progress,
                        )
                        await session.commit()

                        current_share = parse_share

                        async def _progress(stage: str, percent: int, _base=base_progress, _share=current_share, _label=stage_label) -> None:
                            overall = _base + int(percent * _share / 100)
                            await _update_task(
                                session, task,
                                current_stage=f"{_label} {percent}%",
                                progress_percent=min(overall, 50),
                            )
                            await session.commit()

                        await parser.parse_topic(tid, callback=_progress, days=days)

                # Phase 2: Chunking + Analysis (50% → 85%)
                await _update_task(
                    session, task,
                    status="chunk_analysis",
                    current_stage="Подготовка данных для анализа...",
                    progress_percent=50,
                )
                await session.commit()

                # Load posts from all matched topic_ids
                posts_data: list[dict] = []
                seen_topic_ids: set[int] = set()
                for tid in topic_ids_by_source.values():
                    if tid not in seen_topic_ids:
                        seen_topic_ids.add(tid)
                        topic_posts = await _load_posts_as_dicts(session, tid, days=days)
                        posts_data.extend(topic_posts)

                chunks = chunk_data(posts_data, max_tokens=settings.llm_chunk_size)
                total_chunks = len(chunks)
                logger.info(
                    "Topic %s (sources=%s): %d posts, %d chunks",
                    primary_topic_id, sources_label, len(posts_data), total_chunks,
                )
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
                await _update_task(
                    session, task,
                    status="aggregating",
                    current_stage="Формирование итогового отчёта...",
                    progress_percent=85,
                )
                await session.commit()

                report_data = await analyzer.hierarchical_aggregate(partial_results, analysis_mode=analysis_mode)

                # Save report
                if analysis_mode == "niche_search":
                    niche_data = {
                        "key_pains": [p.model_dump() if hasattr(p, "model_dump") else p for p in report_data.get("key_pains", [])],
                        "jtbd_analyses": [j.model_dump() if hasattr(j, "model_dump") else j for j in report_data.get("jtbd_analyses", [])],
                        "business_ideas": [b.model_dump() if hasattr(b, "model_dump") else b for b in report_data.get("business_ideas", [])],
                        "market_trends": [m.model_dump() if hasattr(m, "model_dump") else m for m in report_data.get("market_trends", [])],
                    }
                    db_report = DBReport(
                        topic_id=primary_topic_id,
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
                        topic_id=primary_topic_id,
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

                await _update_task(
                    session, task,
                    status="completed",
                    current_stage="Анализ завершён!",
                    progress_percent=100,
                )
                await session.commit()

            except Exception as exc:
                logger.error("Pipeline failed for topic %s: %s", primary_topic_id, exc, exc_info=True)
                await _update_task(session, task, status="failed", current_stage="Ошибка", error_message=str(exc))
                await session.commit()

    except Exception:
        logger.exception("Background analysis failed for topic %s", primary_topic_id)
