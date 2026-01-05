"""Add retention tracking fields

Revision ID: a5ch44e31f6c
Revises: 94bg33d20e5b
Create Date: 2026-01-02

Law 25 Phase 3: Data Retention Tracking
- last_login_at: Track last successful login
- last_activity_at: Track last authenticated action
- inactivity_warning_sent_at: When warning was sent
- scheduled_anonymization_at: When account will be anonymized
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a5ch44e31f6c"
down_revision: str | None = "94bg33d20e5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add retention tracking fields to users table
    op.add_column(
        "users",
        sa.Column(
            "last_login_at",
            sa.DateTime(),
            nullable=True,
            comment="Last successful login timestamp",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "last_activity_at",
            sa.DateTime(),
            nullable=True,
            comment="Last activity timestamp (any authenticated action)",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "inactivity_warning_sent_at",
            sa.DateTime(),
            nullable=True,
            comment="When inactivity warning email was sent",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "scheduled_anonymization_at",
            sa.DateTime(),
            nullable=True,
            comment="When account is scheduled for anonymization",
        ),
    )

    # Create index for inactive account queries
    op.create_index(
        "ix_users_last_activity_at",
        "users",
        ["last_activity_at"],
    )

    # Backfill last_activity_at with created_at for existing users
    op.execute(
        """
        UPDATE users
        SET last_activity_at = created_at,
            last_login_at = created_at
        WHERE last_activity_at IS NULL
    """
    )


def downgrade() -> None:
    op.drop_index("ix_users_last_activity_at", table_name="users")
    op.drop_column("users", "scheduled_anonymization_at")
    op.drop_column("users", "inactivity_warning_sent_at")
    op.drop_column("users", "last_activity_at")
    op.drop_column("users", "last_login_at")
