"""Add content language field to ideas and comments.

Revision ID: 61ae9a36500a
Revises: 857f77001bb3
Create Date: 2025-12-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "61ae9a36500a"
down_revision: Union[str, None] = "857f77001bb3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add language to ideas with default for existing rows
    op.add_column(
        "ideas",
        sa.Column("language", sa.String(5), nullable=False, server_default="fr"),
    )
    op.create_index("ix_ideas_language", "ideas", ["language"])

    # Add language to comments with default for existing rows
    op.add_column(
        "comments",
        sa.Column("language", sa.String(5), nullable=False, server_default="fr"),
    )


def downgrade() -> None:
    op.drop_index("ix_ideas_language", "ideas")
    op.drop_column("ideas", "language")
    op.drop_column("comments", "language")
