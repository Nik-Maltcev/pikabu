"""Task queue with parallel execution and concurrency limits.

Allows multiple analyses to run in parallel while respecting:
- LLM API rate limits (configurable max concurrent)
- Memory limits (Playwright instances)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from uuid import UUID

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class QueuedTask:
    """A task in the queue."""
    task_id: UUID
    topic_id: int
    coro_factory: Callable[[], Coroutine[Any, Any, None]]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AnalysisQueue:
    """Parallel task queue with concurrency limit.
    
    Runs up to MAX_CONCURRENT_ANALYSES tasks simultaneously.
    New tasks start immediately if under the limit, otherwise wait.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        max_concurrent = settings.max_concurrent_analyses
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._active_tasks: dict[UUID, QueuedTask] = {}
        self._waiting_count = 0
        self._total_processed = 0
        self._initialized = True
        
        logger.info("Analysis queue initialized (max_concurrent=%d)", max_concurrent)
    
    def start_worker(self):
        """No-op for compatibility. Tasks start immediately via run_task()."""
        logger.info("Analysis queue ready (parallel mode, max=%d)", self._max_concurrent)
    
    async def enqueue(
        self,
        task_id: UUID,
        topic_id: int,
        coro_factory: Callable[[], Coroutine[Any, Any, None]],
    ) -> int:
        """Add a task and start it (waits for semaphore if at limit).
        
        Returns:
            Number of tasks waiting (0 = started immediately)
        """
        queued = QueuedTask(
            task_id=task_id,
            topic_id=topic_id,
            coro_factory=coro_factory,
        )
        
        # Start task in background (will wait for semaphore if needed)
        asyncio.create_task(self._run_task(queued))
        
        # Return current waiting count
        waiting = max(0, len(self._active_tasks) - self._max_concurrent + 1)
        logger.info(
            "Task %s enqueued (topic=%s, active=%d, waiting~=%d)",
            task_id, topic_id, len(self._active_tasks), waiting
        )
        
        return waiting
    
    async def _run_task(self, queued: QueuedTask):
        """Execute a task with semaphore control and timeout."""
        self._waiting_count += 1
        
        # Wait for a slot
        async with self._semaphore:
            self._waiting_count -= 1
            self._active_tasks[queued.task_id] = queued
            
            wait_time = (datetime.now(timezone.utc) - queued.created_at).total_seconds()
            logger.info(
                "Task %s starting (topic=%s, waited=%.1fs, active=%d/%d)",
                queued.task_id, queued.topic_id, wait_time,
                len(self._active_tasks), self._max_concurrent
            )
            
            try:
                coro = queued.coro_factory()
                # 30 minute timeout — if task hangs longer, it's dead
                await asyncio.wait_for(coro, timeout=1800)
                self._total_processed += 1
            except asyncio.TimeoutError:
                logger.error("Task %s timed out after 30 minutes", queued.task_id)
            except Exception as e:
                logger.error("Task %s failed: %s", queued.task_id, e)
            finally:
                self._active_tasks.pop(queued.task_id, None)
                logger.info(
                    "Task %s finished (active=%d/%d, total_processed=%d)",
                    queued.task_id, len(self._active_tasks), 
                    self._max_concurrent, self._total_processed
                )
    
    def get_status(self) -> dict:
        """Get current queue status."""
        return {
            "max_concurrent": self._max_concurrent,
            "active_count": len(self._active_tasks),
            "waiting_count": self._waiting_count,
            "total_processed": self._total_processed,
            "active_tasks": [
                {"task_id": str(t.task_id), "topic_id": t.topic_id}
                for t in self._active_tasks.values()
            ],
        }


# Global singleton
analysis_queue = AnalysisQueue()
