"""Add share events table for social media sharing analytics

Revision ID: d7fj66g53h8e
Revises: b6di55f42g7d
Create Date: 2026-01-06

Social Media Sharing Phase 1: Backend - Share Tracking Analytics
- share_events table for tracking social media shares
- Indexed for analytics queries (idea_id + platform, created_at)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7fj66g53h8e"
down_revision: str | None = "b6di55f42g7d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create share_events table
    op.create_table(
        "share_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("idea_id", sa.Integer(), nullable=False),
        sa.Column(
            "platform",
            sa.Enum(
                "TWITTER",
                "FACEBOOK",
                "LINKEDIN",
                "WHATSAPP",
                "COPY_LINK",
                name="shareplatform",
            ),
            nullable=False,
        ),
        sa.Column(
            "referrer_url",
            sa.String(500),
            nullable=True,
            comment="URL where share was initiated",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["idea_id"],
            ["ideas.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for analytics queries
    op.create_index(
        "ix_share_events_idea_platform",
        "share_events",
        ["idea_id", "platform"],
    )
    op.create_index(
        "ix_share_events_created_at",
        "share_events",
        ["created_at"],
    )
    op.create_index(
        op.f("ix_share_events_id"),
        "share_events",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_share_events_id"), table_name="share_events")
    op.drop_index("ix_share_events_created_at", table_name="share_events")
    op.drop_index("ix_share_events_idea_platform", table_name="share_events")
    op.drop_table("share_events")

    # Drop the enum type (PostgreSQL specific, SQLite ignores)
    op.execute("DROP TYPE IF EXISTS shareplatform")
