"""add_source_columns

Revision ID: b1c2d3e4f5a6
Revises: 3a835815ef7e
Create Date: 2026-04-14 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "3a835815ef7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "topics",
        sa.Column("source", sa.String(20), nullable=False, server_default="pikabu"),
    )
    op.create_index("idx_topics_source", "topics", ["source"])

    op.add_column(
        "posts",
        sa.Column("source", sa.String(20), nullable=False, server_default="pikabu"),
    )
    op.create_index("idx_posts_source", "posts", ["source"])

    op.add_column(
        "reports",
        sa.Column("sources", sa.String(50), nullable=False, server_default="pikabu"),
    )


def downgrade() -> None:
    op.drop_column("reports", "sources")

    op.drop_index("idx_posts_source", table_name="posts")
    op.drop_column("posts", "source")

    op.drop_index("idx_topics_source", table_name="topics")
    op.drop_column("topics", "source")
