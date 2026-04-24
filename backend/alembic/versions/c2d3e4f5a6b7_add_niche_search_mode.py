"""add_niche_search_mode

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-04-24 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Поле analysis_mode в analysis_tasks
    op.add_column(
        "analysis_tasks",
        sa.Column("analysis_mode", sa.String(30), nullable=False, server_default="topic_analysis"),
    )

    # Поля analysis_mode и niche_data в reports
    op.add_column(
        "reports",
        sa.Column("analysis_mode", sa.String(30), nullable=False, server_default="topic_analysis"),
    )
    op.add_column(
        "reports",
        sa.Column("niche_data", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reports", "niche_data")
    op.drop_column("reports", "analysis_mode")
    op.drop_column("analysis_tasks", "analysis_mode")
