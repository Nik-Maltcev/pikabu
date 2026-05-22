"""Built-in scheduler for background tasks.

Runs parsing every 3 days automatically without external cron services.
"""

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Global state
_scheduler_task = None
_last_parse_time = None


async def _run_scheduled_parse():
    """Run the scheduled parsing job."""
    from app.services.background_parser import run_full_parse, run_cleanup
    
    global _last_parse_time
    
    logger.info("Scheduled parse starting...")
    _last_parse_time = datetime.now(timezone.utc)
    
    try:
        # Parse all categories (30 days)
        stats = await run_full_parse(days=30)
        logger.info("Scheduled parse completed: %s", stats)
        
        # Cleanup old posts (older than 35 days)
        cleanup_stats = await run_cleanup(days=35)
        logger.info("Scheduled cleanup completed: %s", cleanup_stats)
        
    except Exception as e:
        logger.error("Scheduled parse failed: %s", e)


async def _scheduler_loop():
    """Main scheduler loop. Runs every 3 days."""
    # Wait 30 seconds after startup before first check
    await asyncio.sleep(30)
    
    # Parse interval: 3 days in seconds
    PARSE_INTERVAL = 3 * 24 * 60 * 60  # 259200 seconds
    
    while True:
        try:
            # Check if we need to parse
            should_parse = False
            
            if _last_parse_time is None:
                # Never parsed, check DB
                from app.database import async_session
                from app.models.database import ParseMetadata
                from sqlalchemy import select, func
                
                try:
                    async with async_session() as session:
                        result = await session.execute(
                            select(func.max(ParseMetadata.last_parsed_at))
                        )
                        last_db_parse = result.scalar()
                        
                        if last_db_parse is None:
                            # Never parsed at all
                            should_parse = True
                            logger.info("No previous parse found, will parse now")
                        else:
                            # Check if 3 days passed
                            age = (datetime.now(timezone.utc) - last_db_parse).total_seconds()
                            if age > PARSE_INTERVAL:
                                should_parse = True
                                logger.info("Last parse was %.1f days ago, will parse now", age / 86400)
                except Exception as db_err:
                    logger.warning("Could not check parse_metadata table: %s. Will parse.", db_err)
                    should_parse = True
            else:
                # Check against in-memory last parse time
                age = (datetime.now(timezone.utc) - _last_parse_time).total_seconds()
                if age > PARSE_INTERVAL:
                    should_parse = True
            
            if should_parse:
                await _run_scheduled_parse()
            
        except Exception as e:
            logger.error("Scheduler error: %s", e)
        
        # Check every hour
        await asyncio.sleep(3600)


def start_scheduler():
    """Start the background scheduler."""
    global _scheduler_task
    
    if _scheduler_task is not None:
        logger.warning("Scheduler already running")
        return
    
    _scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("Background scheduler started (parse every 3 days)")


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler_task
    
    if _scheduler_task is not None:
        _scheduler_task.cancel()
        _scheduler_task = None
        logger.info("Background scheduler stopped")


def get_scheduler_status() -> dict:
    """Get current scheduler status."""
    return {
        "running": _scheduler_task is not None and not _scheduler_task.done(),
        "last_parse_time": _last_parse_time.isoformat() if _last_parse_time else None,
        "parse_interval_days": 3,
    }
