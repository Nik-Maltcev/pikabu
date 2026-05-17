"""Background parser — pre-parses all categories on schedule.

Runs weekly to populate the database with fresh posts and comments.
Also provides incremental comment updates for existing posts.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Callable, Awaitable

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.database import Topic, Post, Comment, ParseMetadata
from app.services.parser import ParserService
from app.services.habr_parser import HabrParserService
from app.services.vcru_parser import VcruParserService
from app.services.playwright_renderer import PlaywrightRenderer

logger = logging.getLogger(__name__)

# Type alias for progress callbacks
ProgressCallback = Callable[[str, int, str], Awaitable[None]] | None


class BackgroundParser:
    """Handles scheduled parsing of all categories and incremental updates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Full parsing (weekly cron job)
    # ------------------------------------------------------------------

    async def parse_all_categories(
        self,
        days: int = 30,
        callback: ProgressCallback = None,
    ) -> dict:
        """Parse ALL categories from all platforms.

        This is meant to run weekly via cron job.
        Parses posts from last N days and all their comments.

        Returns summary stats.
        """
        stats = {
            "total_topics": 0,
            "total_posts": 0,
            "total_comments": 0,
            "errors": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        # Get all topics
        result = await self._session.execute(select(Topic).order_by(Topic.source, Topic.name))
        topics = list(result.scalars().all())
        stats["total_topics"] = len(topics)

        logger.info("Starting full parse of %d topics for %d days", len(topics), days)

        for i, topic in enumerate(topics):
            topic_name = f"{topic.source}:{topic.name}"
            
            if callback:
                progress = int((i / len(topics)) * 100)
                await callback("parsing", progress, topic_name)

            try:
                result = await self._parse_single_topic(topic, days)
                stats["total_posts"] += result["posts_count"]
                stats["total_comments"] += result["comments_count"]
                logger.info(
                    "Parsed %s: %d posts, %d comments",
                    topic_name, result["posts_count"], result["comments_count"]
                )
            except Exception as e:
                error_msg = f"{topic_name}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error("Failed to parse %s: %s", topic_name, e)

            # Delay between topics to avoid rate limits
            await asyncio.sleep(5)

        stats["finished_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            "Full parse complete: %d posts, %d comments, %d errors",
            stats["total_posts"], stats["total_comments"], len(stats["errors"])
        )

        return stats

    async def _parse_single_topic(self, topic: Topic, days: int) -> dict:
        """Parse a single topic using the appropriate parser."""
        if topic.source == "pikabu":
            parser = ParserService(self._session)
            return await parser.parse_topic(topic.id, days=days)
        elif topic.source == "habr":
            parser = HabrParserService(self._session)
            return await parser.parse_topic(topic.id, days=days)
        elif topic.source == "vcru":
            parser = VcruParserService(self._session)
            return await parser.parse_topic(topic.id, days=days)
        else:
            raise ValueError(f"Unknown source: {topic.source}")

    # ------------------------------------------------------------------
    # Incremental comment updates (on-demand)
    # ------------------------------------------------------------------

    async def update_comments_for_topic(
        self,
        topic_id: int,
        days: int = 30,
        callback: ProgressCallback = None,
    ) -> dict:
        """Update comments for existing posts in a topic.

        Only fetches comments for posts that have new comments
        (based on comments_count comparison).

        This is MUCH faster than full parsing since we skip:
        - Fetching post listings
        - Posts with no new comments
        """
        topic = await self._get_topic(topic_id)
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")

        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Get posts from DB that are within the date range
        result = await self._session.execute(
            select(Post)
            .where(Post.topic_id == topic_id)
            .where(Post.published_at >= since)
            .order_by(Post.published_at.desc())
        )
        posts = list(result.scalars().all())

        if not posts:
            logger.info("No posts found for topic %d in last %d days", topic_id, days)
            return {"posts_checked": 0, "posts_updated": 0, "new_comments": 0}

        stats = {
            "posts_checked": len(posts),
            "posts_updated": 0,
            "new_comments": 0,
        }

        logger.info("Checking %d posts for new comments (topic=%d)", len(posts), topic_id)

        # Use appropriate parser based on source
        async with PlaywrightRenderer() as renderer:
            for i, post in enumerate(posts):
                if callback:
                    progress = int((i / len(posts)) * 100)
                    await callback("updating_comments", progress, post.title[:50])

                try:
                    new_count = await self._update_post_comments(post, topic.source, renderer)
                    if new_count > 0:
                        stats["posts_updated"] += 1
                        stats["new_comments"] += new_count
                except Exception as e:
                    logger.warning("Failed to update comments for post %s: %s", post.id, e)

                # Small delay between posts
                await asyncio.sleep(1)

        logger.info(
            "Comment update complete for topic %d: %d posts updated, %d new comments",
            topic_id, stats["posts_updated"], stats["new_comments"]
        )

        return stats

    async def _update_post_comments(
        self,
        post: Post,
        source: str,
        renderer: PlaywrightRenderer,
    ) -> int:
        """Check and update comments for a single post.

        Returns number of new comments added.
        """
        # Count existing comments in DB
        result = await self._session.execute(
            select(func.count(Comment.id)).where(Comment.post_id == post.id)
        )
        db_comment_count = result.scalar() or 0

        # If DB has same or more comments than post.comments_count, skip
        # (comments_count is from the last parse)
        if db_comment_count >= post.comments_count:
            return 0

        # Fetch fresh comments
        comments_data = await self._fetch_comments(post.url, source, renderer)

        if not comments_data:
            return 0

        # Get existing comment IDs
        result = await self._session.execute(
            select(Comment.pikabu_comment_id).where(Comment.post_id == post.id)
        )
        existing_ids = set(row[0] for row in result.fetchall())

        # Add only new comments
        new_count = 0
        for comment_data in comments_data:
            if comment_data["pikabu_comment_id"] not in existing_ids:
                comment = Comment(
                    post_id=post.id,
                    pikabu_comment_id=comment_data["pikabu_comment_id"],
                    body=comment_data["body"],
                    published_at=comment_data["published_at"],
                    rating=comment_data["rating"],
                )
                self._session.add(comment)
                new_count += 1

        if new_count > 0:
            # Update post's comments_count
            post.comments_count = len(comments_data)
            await self._session.flush()

        return new_count

    async def _fetch_comments(
        self,
        post_url: str,
        source: str,
        renderer: PlaywrightRenderer,
    ) -> list[dict]:
        """Fetch comments using the appropriate parser."""
        if source == "pikabu":
            parser = ParserService(self._session)
            return await parser.parse_comments(post_url)
        elif source == "habr":
            parser = HabrParserService(self._session)
            return await parser.parse_comments(post_url, renderer=renderer)
        elif source == "vcru":
            parser = VcruParserService(self._session)
            return await parser.parse_comments(post_url, renderer)
        else:
            return []

    # ------------------------------------------------------------------
    # Cleanup old data
    # ------------------------------------------------------------------

    async def cleanup_old_posts(self, days: int = 35) -> dict:
        """Delete posts older than N days.

        Uses 35 days by default to keep a buffer beyond the 30-day analysis window.
        Comments are deleted automatically via CASCADE.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Count before delete
        result = await self._session.execute(
            select(func.count(Post.id)).where(Post.published_at < cutoff)
        )
        posts_to_delete = result.scalar() or 0

        if posts_to_delete == 0:
            return {"deleted_posts": 0}

        # Delete old posts (comments cascade)
        await self._session.execute(
            delete(Post).where(Post.published_at < cutoff)
        )
        await self._session.commit()

        logger.info("Cleaned up %d posts older than %d days", posts_to_delete, days)

        return {"deleted_posts": posts_to_delete}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_topic(self, topic_id: int) -> Topic | None:
        result = await self._session.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        return result.scalar_one_or_none()

    async def get_parse_status(self) -> dict:
        """Get current parsing status for all topics."""
        result = await self._session.execute(
            select(
                Topic.id,
                Topic.name,
                Topic.source,
                ParseMetadata.last_parsed_at,
                ParseMetadata.posts_count,
                ParseMetadata.comments_count,
            )
            .outerjoin(ParseMetadata, Topic.id == ParseMetadata.topic_id)
            .order_by(Topic.source, Topic.name)
        )
        rows = result.fetchall()

        topics = []
        for row in rows:
            topics.append({
                "topic_id": row[0],
                "name": row[1],
                "source": row[2],
                "last_parsed_at": row[3].isoformat() if row[3] else None,
                "posts_count": row[4] or 0,
                "comments_count": row[5] or 0,
            })

        # Summary stats
        total_posts = sum(t["posts_count"] for t in topics)
        total_comments = sum(t["comments_count"] for t in topics)
        parsed_topics = sum(1 for t in topics if t["last_parsed_at"])

        return {
            "topics": topics,
            "summary": {
                "total_topics": len(topics),
                "parsed_topics": parsed_topics,
                "total_posts": total_posts,
                "total_comments": total_comments,
            }
        }


# ------------------------------------------------------------------
# Standalone runner for cron jobs
# ------------------------------------------------------------------

async def run_full_parse(days: int = 30) -> dict:
    """Run full parse of all categories. Called by cron endpoint."""
    async with async_session() as session:
        parser = BackgroundParser(session)
        stats = await parser.parse_all_categories(days=days)
        await session.commit()
        return stats


async def run_cleanup(days: int = 35) -> dict:
    """Run cleanup of old posts. Called by cron endpoint."""
    async with async_session() as session:
        parser = BackgroundParser(session)
        stats = await parser.cleanup_old_posts(days=days)
        return stats
