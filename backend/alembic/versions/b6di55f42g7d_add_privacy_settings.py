"""Add privacy settings fields

Revision ID: b6di55f42g7d
Revises: a5ch44e31f6c
Create Date: 2026-01-02

Law 25 Phase 4: Privacy Settings
- profile_visibility: Control who can see profile (public, registered, private)
- show_display_name: Show/hide display name publicly
- show_avatar: Show/hide avatar publicly
- show_activity: Show/hide ideas and comments count
- show_join_date: Show/hide account creation date
- policy_versions table: Track legal document versions for re-consent
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b6di55f42g7d"
down_revision: str | None = "a5ch44e31f6c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add privacy settings fields to users table
    op.add_column(
        "users",
        sa.Column(
            "profile_visibility",
            sa.String(20),
            nullable=False,
            server_default="public",
            comment="Profile visibility: public, registered, private",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "show_display_name",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment="Show display name on public profile",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "show_avatar",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment="Show avatar on public profile",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "show_activity",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment="Show activity (ideas, comments) on public profile",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "show_join_date",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment="Show account creation date on public profile",
        ),
    )

    # Create policy_versions table
    op.create_table(
        "policy_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "policy_type",
            sa.String(20),
            nullable=False,
            comment="Type: 'privacy' or 'terms'",
        ),
        sa.Column(
            "version",
            sa.String(20),
            nullable=False,
            comment="Version number (e.g., '1.0', '1.1')",
        ),
        sa.Column(
            "effective_date",
            sa.DateTime(),
            nullable=False,
            comment="When this version becomes effective",
        ),
        sa.Column(
            "summary_en",
            sa.Text(),
            nullable=True,
            comment="Summary of changes in English",
        ),
        sa.Column(
            "summary_fr",
            sa.Text(),
            nullable=True,
            comment="Summary of changes in French",
        ),
        sa.Column(
            "requires_reconsent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="Whether users need to re-consent to this version",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("policy_type", "version", name="uq_policy_version"),
    )

    # Create index on policy_versions
    op.create_index(
        "ix_policy_versions_type",
        "policy_versions",
        ["policy_type"],
    )

    # Insert initial policy versions
    op.execute(
        """
        INSERT INTO policy_versions (policy_type, version, effective_date, requires_reconsent, created_at)
        VALUES
        ('privacy', '1.0', '2025-01-01', 0, CURRENT_TIMESTAMP),
        ('terms', '1.0', '2025-01-01', 0, CURRENT_TIMESTAMP)
    """
    )


def downgrade() -> None:
    op.drop_index("ix_policy_versions_type", table_name="policy_versions")
    op.drop_table("policy_versions")
    op.drop_column("users", "show_join_date")
    op.drop_column("users", "show_activity")
    op.drop_column("users", "show_avatar")
    op.drop_column("users", "show_display_name")
    op.drop_column("users", "profile_visibility")
