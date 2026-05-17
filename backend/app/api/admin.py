"""Admin API — view tasks and contacts."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.database import AnalysisTask, Report as DBReport, Topic as DBTopic
from app.services.task_queue import analysis_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin")


class TaskInfo(BaseModel):
    """Task info for admin view."""
    task_id: str
    topic_id: int | None
    topic_name: str | None
    status: str
    progress_percent: int
    contact_type: str | None
    contact_value: str | None
    created_at: str
    report_id: int | None
    report_url: str | None


class TaskListResponse(BaseModel):
    """Response with list of tasks."""
    tasks: list[TaskInfo]
    total: int


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: str = Query(default="", description="Filter by status"),
    has_contact: bool = Query(default=False, description="Only tasks with contact"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> TaskListResponse:
    """List all analysis tasks with contact info."""
    query = select(AnalysisTask).order_by(desc(AnalysisTask.created_at))
    
    if status:
        query = query.where(AnalysisTask.status == status)
    
    if has_contact:
        query = query.where(AnalysisTask.contact_value.isnot(None))
        query = query.where(AnalysisTask.contact_value != "")
    
    # Count
    from sqlalchemy import func
    count_query = select(func.count(AnalysisTask.id))
    if status:
        count_query = count_query.where(AnalysisTask.status == status)
    if has_contact:
        count_query = count_query.where(AnalysisTask.contact_value.isnot(None))
        count_query = count_query.where(AnalysisTask.contact_value != "")
    
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    tasks = result.scalars().all()
    
    task_infos = []
    for task in tasks:
        topic_name = None
        if task.topic_id:
            topic_result = await session.execute(
                select(DBTopic.name).where(DBTopic.id == task.topic_id)
            )
            topic_name = topic_result.scalar_one_or_none()
        
        report_id = None
        report_url = None
        if task.status == "completed":
            report_result = await session.execute(
                select(DBReport.id).where(DBReport.task_id == task.id)
            )
            report_id = report_result.scalar_one_or_none()
            if report_id and task.topic_id:
                report_url = f"{settings.site_url}/reports/{task.topic_id}/{report_id}"
        
        task_infos.append(TaskInfo(
            task_id=str(task.id),
            topic_id=task.topic_id,
            topic_name=topic_name,
            status=task.status,
            progress_percent=task.progress_percent,
            contact_type=task.contact_type,
            contact_value=task.contact_value,
            created_at=task.created_at.isoformat() if task.created_at else "",
            report_id=report_id,
            report_url=report_url,
        ))
    
    return TaskListResponse(tasks=task_infos, total=total)


@router.get("/contacts/export")
async def export_contacts(
    format: str = Query(default="json", description="json or csv"),
    session: AsyncSession = Depends(get_session),
):
    """Export unique contacts."""
    query = select(AnalysisTask).where(
        AnalysisTask.contact_value.isnot(None),
        AnalysisTask.contact_value != "",
    ).order_by(desc(AnalysisTask.created_at))
    
    result = await session.execute(query)
    tasks = result.scalars().all()
    
    contacts = []
    seen = set()
    
    for task in tasks:
        key = f"{task.contact_type}:{task.contact_value}"
        if key in seen:
            continue
        seen.add(key)
        
        topic_name = None
        if task.topic_id:
            topic_result = await session.execute(
                select(DBTopic.name).where(DBTopic.id == task.topic_id)
            )
            topic_name = topic_result.scalar_one_or_none()
        
        contacts.append({
            "contact_type": task.contact_type,
            "contact_value": task.contact_value,
            "topic_name": topic_name,
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else "",
        })
    
    if format == "csv":
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["contact_type", "contact_value", "topic_name", "status", "created_at"])
        writer.writeheader()
        writer.writerows(contacts)
        
        from fastapi.responses import Response
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=contacts.csv"}
        )
    
    return {"contacts": contacts, "total": len(contacts)}



@router.get("/queue")
async def get_queue_status():
    """Get current analysis queue status."""
    return analysis_queue.get_status()


@router.get("/db-status")
async def get_db_status(
    session: AsyncSession = Depends(get_session),
):
    """Get database status (posts, comments counts)."""
    from sqlalchemy import func
    from app.models.database import Post, Comment, ParseMetadata
    from app.services.scheduler import get_scheduler_status
    
    # Count topics
    topics_result = await session.execute(select(func.count(DBTopic.id)))
    total_topics = topics_result.scalar() or 0
    
    # Count posts
    posts_result = await session.execute(select(func.count(Post.id)))
    total_posts = posts_result.scalar() or 0
    
    # Count comments
    comments_result = await session.execute(select(func.count(Comment.id)))
    total_comments = comments_result.scalar() or 0
    
    # Count parsed topics (have ParseMetadata)
    parsed_result = await session.execute(select(func.count(ParseMetadata.id)))
    parsed_topics = parsed_result.scalar() or 0
    
    # Get last parse time
    last_parse_result = await session.execute(
        select(func.max(ParseMetadata.last_parsed_at))
    )
    last_parse = last_parse_result.scalar()
    
    # Scheduler status
    scheduler = get_scheduler_status()
    
    return {
        "total_topics": total_topics,
        "total_posts": total_posts,
        "total_comments": total_comments,
        "parsed_topics": parsed_topics,
        "last_parse_at": last_parse.isoformat() if last_parse else None,
        "scheduler": scheduler,
    }
