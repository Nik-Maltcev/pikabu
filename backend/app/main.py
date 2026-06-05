import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router as api_router
from app.api.payment import router as payment_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.cron import router as cron_router
from app.api.chat import router as chat_router
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Starting Pikabu Topic Analyzer...")
logger.info("PORT=%s", os.environ.get("PORT", "not set"))
logger.info("DATABASE_URL=%s", "***" if settings.database_url else "not set")

logger.info("CORS_ORIGINS=%s", settings.cors_origins_list)

app = FastAPI(
    title="Pikabu Topic Analyzer",
    description="API для анализа контента pikabu.ru по выбранной теме",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(payment_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(cron_router)
app.include_router(chat_router)


@app.on_event("startup")
async def on_startup():
    """Create database tables if they don't exist, add missing columns, start queue worker."""
    from app.database import engine
    from app.models.database import Base
    from sqlalchemy import text
    from app.services.task_queue import analysis_queue
    from app.services.scheduler import start_scheduler

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Add source columns if they don't exist (for existing DBs without migration)
        for stmt in [
            "ALTER TABLE topics ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'pikabu'",
            "ALTER TABLE posts ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'pikabu'",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS sources VARCHAR(50) NOT NULL DEFAULT 'pikabu'",
            "ALTER TABLE analysis_tasks ADD COLUMN IF NOT EXISTS analysis_mode VARCHAR(30) NOT NULL DEFAULT 'topic_analysis'",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS analysis_mode VARCHAR(30) NOT NULL DEFAULT 'topic_analysis'",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS niche_data JSONB",
            "ALTER TABLE payments ALTER COLUMN report_id DROP NOT NULL",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS topic_id INTEGER",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS task_id VARCHAR(64)",
            "ALTER TABLE reports ADD COLUMN IF NOT EXISTS user_id INTEGER",
            # Contact columns for notifications
            "ALTER TABLE analysis_tasks ADD COLUMN IF NOT EXISTS contact_type VARCHAR(20)",
            "ALTER TABLE analysis_tasks ADD COLUMN IF NOT EXISTS contact_value VARCHAR(255)",
            # User email/password auth columns
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)",
            "ALTER TABLE users ALTER COLUMN phone DROP NOT NULL",
            # Analysis task user_id for linking
            "ALTER TABLE analysis_tasks ADD COLUMN IF NOT EXISTS user_id INTEGER",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS promo_code VARCHAR(50)",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS questions_used INTEGER DEFAULT 0",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # Column already exists or DB doesn't support IF NOT EXISTS

    logger.info("Database tables ensured.")
    
    # Start the analysis queue worker
    analysis_queue.start_worker()
    logger.info("Analysis queue worker started.")
    
    # Start the background scheduler (parses every 3 days)
    start_scheduler()
    logger.info("Background scheduler started.")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
