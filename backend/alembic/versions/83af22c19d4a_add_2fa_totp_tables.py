"""Add 2FA TOTP tables for two-factor authentication.

Revision ID: 83af22c19d4a
Revises: 72bf99112cc1
Create Date: 2025-12-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "83af22c19d4a"
down_revision: Union[str, None] = "72bf99112cc1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add totp_enabled column to users table
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Create user_totp_secrets table
    op.create_table(
        "user_totp_secrets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("encrypted_secret", sa.String(256), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_user_totp_secrets_id", "user_totp_secrets", ["id"])

    # Create user_backup_codes table
    op.create_table(
        "user_backup_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_backup_codes_id", "user_backup_codes", ["id"])
    op.create_index(
        "idx_backup_codes_user_unused", "user_backup_codes", ["user_id", "used_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_backup_codes_user_unused", "user_backup_codes")
    op.drop_index("ix_user_backup_codes_id", "user_backup_codes")
    op.drop_table("user_backup_codes")

    op.drop_index("ix_user_totp_secrets_id", "user_totp_secrets")
    op.drop_table("user_totp_secrets")

    op.drop_column("users", "totp_enabled")
