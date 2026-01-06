"""Add edit tracking columns for approved idea editing

Revision ID: e8gk77h64i9f
Revises: d7fj66g53h8e
Create Date: 2026-01-06

This migration adds columns to support editing approved ideas with re-moderation:
- edit_count: Number of times idea has been edited after approval
- last_edit_at: Timestamp of the last edit
- previous_status: Status before transitioning to PENDING_EDIT (for restoration)

The IdeaStatus enum is also extended with PENDING_EDIT value.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e8gk77h64i9f"
down_revision = "d7fj66g53h8e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add edit tracking columns to ideas table
    op.add_column(
        "ideas",
        sa.Column(
            "edit_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of times this idea has been edited after approval",
        ),
    )
    op.add_column(
        "ideas",
        sa.Column(
            "last_edit_at",
            sa.DateTime(),
            nullable=True,
            comment="Timestamp of the last edit",
        ),
    )
    op.add_column(
        "ideas",
        sa.Column(
            "previous_status",
            sa.String(20),
            nullable=True,
            comment="Status before transitioning to PENDING_EDIT (for restoration)",
        ),
    )

    # Note: SQLite handles enum values as strings, so no ALTER TYPE needed.
    # The new PENDING_EDIT status value is already defined in the Python enum
    # and will work automatically with SQLite string storage.


def downgrade() -> None:
    # Remove edit tracking columns
    op.drop_column("ideas", "previous_status")
    op.drop_column("ideas", "last_edit_at")
    op.drop_column("ideas", "edit_count")

    # Note: Any ideas with status='pending_edit' will become invalid after downgrade.
    # Consider updating them to 'pending' before running downgrade in production.
