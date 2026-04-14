"""initial_schema

Revision ID: 3a835815ef7e
Revises:
Create Date: 2026-04-13 18:35:24.022545

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "3a835815ef7e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pikabu_id", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("subscribers_count", sa.Integer(), nullable=True),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("pikabu_post_id", sa.String(255), unique=True, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rating", sa.Integer(), server_default="0"),
        sa.Column("comments_count", sa.Integer(), server_default="0"),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column(
            "parsed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_posts_topic_id", "posts", ["topic_id"])
    op.create_index("idx_posts_published_at", "posts", ["published_at"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "post_id",
            sa.Integer(),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("pikabu_comment_id", sa.String(255), unique=True, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rating", sa.Integer(), server_default="0"),
        sa.Column(
            "parsed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_comments_post_id", "comments", ["post_id"])

    op.create_table(
        "analysis_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "status", sa.String(50), nullable=False, server_default="pending"
        ),
        sa.Column("progress_percent", sa.Integer(), server_default="0"),
        sa.Column("current_stage", sa.String(100), nullable=True),
        sa.Column("total_chunks", sa.Integer(), nullable=True),
        sa.Column("processed_chunks", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_analysis_tasks_topic_id", "analysis_tasks", ["topic_id"])
    op.create_index("idx_analysis_tasks_status", "analysis_tasks", ["status"])

    op.create_table(
        "partial_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_tasks.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column(
            "topics_found",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "user_problems",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "active_discussions",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_tasks.id"),
            nullable=True,
        ),
        sa.Column(
            "hot_topics",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "user_problems",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "trending_discussions",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_reports_topic_id", "reports", ["topic_id"])
    op.create_index("idx_reports_generated_at", "reports", ["generated_at"])

    op.create_table(
        "parse_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            unique=True,
            nullable=True,
        ),
        sa.Column("last_parsed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("posts_count", sa.Integer(), server_default="0"),
        sa.Column("comments_count", sa.Integer(), server_default="0"),
    )
    op.create_index("idx_parse_metadata_topic_id", "parse_metadata", ["topic_id"])


def downgrade() -> None:
    op.drop_table("parse_metadata")
    op.drop_table("reports")
    op.drop_table("partial_results")
    op.drop_table("analysis_tasks")
    op.drop_table("comments")
    op.drop_table("posts")
    op.drop_table("topics")
