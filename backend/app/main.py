import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router as api_router
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
async def on_startup():
    """Create database tables if they don't exist, add missing columns."""
    from app.database import engine
    from app.models.database import Base
    from sqlalchemy import text

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
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # Column already exists or DB doesn't support IF NOT EXISTS

    logger.info("Database tables ensured.")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
