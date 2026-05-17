"""Cron API — endpoints for scheduled tasks.

These endpoints are called by Railway/Render cron jobs or external schedulers.
Protected by a secret token to prevent unauthorized access.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel

from app.config import settings
from app.services.background_parser import run_full_parse, run_cleanup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cron")


class CronResponse(BaseModel):
    """Response from cron endpoints."""
    status: str
    message: str
    started_at: str | None = None


class ParseStatusResponse(BaseModel):
    """Response with parse job status."""
    status: str
    stats: dict | None = None


# Global state for tracking parse job
_parse_job_status = {
    "running": False,
    "last_run": None,
    "last_stats": None,
}


def _verify_cron_secret(authorization: str | None) -> None:
    """Verify the cron secret token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Accept "Bearer <token>" or just "<token>"
    token = authorization.replace("Bearer ", "").strip()
    
    if token != settings.cron_secret:
        raise HTTPException(status_code=403, detail="Invalid cron secret")


@router.post("/parse-all", response_model=CronResponse)
async def trigger_full_parse(
    background_tasks: BackgroundTasks,
    days: int = 30,
    authorization: str | None = Header(default=None),
):
    """Trigger full parsing of all categories.

    This endpoint starts the parse job in the background and returns immediately.
    Use GET /api/cron/parse-status to check progress.

    Args:
        days: Number of days to parse (default 30)
        authorization: Bearer token with CRON_SECRET
    """
    _verify_cron_secret(authorization)

    if _parse_job_status["running"]:
        return CronResponse(
            status="already_running",
            message="Parse job is already running",
            started_at=_parse_job_status["last_run"],
        )

    async def _run_parse():
        global _parse_job_status
        _parse_job_status["running"] = True
        _parse_job_status["last_run"] = datetime.now(timezone.utc).isoformat()
        
        try:
            stats = await run_full_parse(days=days)
            _parse_job_status["last_stats"] = stats
            logger.info("Full parse completed: %s", stats)
        except Exception as e:
            logger.error("Full parse failed: %s", e)
            _parse_job_status["last_stats"] = {"error": str(e)}
        finally:
            _parse_job_status["running"] = False

    background_tasks.add_task(_run_parse)

    return CronResponse(
        status="started",
        message=f"Full parse started for {days} days",
        started_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/parse-status", response_model=ParseStatusResponse)
async def get_parse_status(
    authorization: str | None = Header(default=None),
):
    """Get status of the current/last parse job."""
    _verify_cron_secret(authorization)

    if _parse_job_status["running"]:
        return ParseStatusResponse(
            status="running",
            stats={"started_at": _parse_job_status["last_run"]},
        )

    if _parse_job_status["last_stats"]:
        return ParseStatusResponse(
            status="completed",
            stats=_parse_job_status["last_stats"],
        )

    return ParseStatusResponse(
        status="idle",
        stats=None,
    )


@router.post("/cleanup", response_model=CronResponse)
async def trigger_cleanup(
    days: int = 35,
    authorization: str | None = Header(default=None),
):
    """Delete posts older than N days.

    Args:
        days: Delete posts older than this (default 35)
        authorization: Bearer token with CRON_SECRET
    """
    _verify_cron_secret(authorization)

    try:
        stats = await run_cleanup(days=days)
        return CronResponse(
            status="completed",
            message=f"Cleanup completed: {stats['deleted_posts']} posts deleted",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error("Cleanup failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse-and-cleanup", response_model=CronResponse)
async def trigger_parse_and_cleanup(
    background_tasks: BackgroundTasks,
    parse_days: int = 30,
    cleanup_days: int = 35,
    authorization: str | None = Header(default=None),
):
    """Combined endpoint: parse all categories then cleanup old data.

    This is the recommended weekly cron job.

    Args:
        parse_days: Number of days to parse (default 30)
        cleanup_days: Delete posts older than this (default 35)
        authorization: Bearer token with CRON_SECRET
    """
    _verify_cron_secret(authorization)

    if _parse_job_status["running"]:
        return CronResponse(
            status="already_running",
            message="Parse job is already running",
            started_at=_parse_job_status["last_run"],
        )

    async def _run_parse_and_cleanup():
        global _parse_job_status
        _parse_job_status["running"] = True
        _parse_job_status["last_run"] = datetime.now(timezone.utc).isoformat()

        try:
            # Step 1: Full parse
            logger.info("Starting full parse for %d days", parse_days)
            parse_stats = await run_full_parse(days=parse_days)
            logger.info("Full parse completed: %s", parse_stats)

            # Step 2: Cleanup
            logger.info("Starting cleanup for posts older than %d days", cleanup_days)
            cleanup_stats = await run_cleanup(days=cleanup_days)
            logger.info("Cleanup completed: %s", cleanup_stats)

            _parse_job_status["last_stats"] = {
                "parse": parse_stats,
                "cleanup": cleanup_stats,
            }
        except Exception as e:
            logger.error("Parse and cleanup failed: %s", e)
            _parse_job_status["last_stats"] = {"error": str(e)}
        finally:
            _parse_job_status["running"] = False

    background_tasks.add_task(_run_parse_and_cleanup)

    return CronResponse(
        status="started",
        message=f"Parse ({parse_days} days) and cleanup ({cleanup_days} days) started",
        started_at=datetime.now(timezone.utc).isoformat(),
    )
