"""Add consent management fields for Law 25 compliance.

Revision ID: 94bg33d20e5b
Revises: 83af22c19d4a
Create Date: 2026-01-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "94bg33d20e5b"
down_revision: Union[str, None] = "83af22c19d4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add consent fields to users table
    op.add_column(
        "users",
        sa.Column(
            "consent_terms_accepted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "consent_privacy_accepted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "users",
        sa.Column("consent_terms_version", sa.String(20), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("consent_privacy_version", sa.String(20), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("consent_timestamp", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "marketing_consent",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "users",
        sa.Column("marketing_consent_timestamp", sa.DateTime(), nullable=True),
    )

    # Create consent_logs table for audit trail
    op.create_table(
        "consent_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("consent_type", sa.String(50), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("policy_version", sa.String(20), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_consent_logs_user_id", "consent_logs", ["user_id"])
    op.create_index("ix_consent_logs_created_at", "consent_logs", ["created_at"])

    # Backfill existing users with default consent (they implicitly agreed by using the platform)
    # In production, you may want to require re-consent instead
    op.execute("""
        UPDATE users
        SET consent_terms_accepted = 1,
            consent_privacy_accepted = 1,
            consent_terms_version = '1.0',
            consent_privacy_version = '1.0',
            consent_timestamp = created_at
        WHERE consent_timestamp IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_consent_logs_created_at", "consent_logs")
    op.drop_index("ix_consent_logs_user_id", "consent_logs")
    op.drop_table("consent_logs")
    op.drop_column("users", "marketing_consent_timestamp")
    op.drop_column("users", "marketing_consent")
    op.drop_column("users", "consent_timestamp")
    op.drop_column("users", "consent_privacy_version")
    op.drop_column("users", "consent_terms_version")
    op.drop_column("users", "consent_privacy_accepted")
    op.drop_column("users", "consent_terms_accepted")
