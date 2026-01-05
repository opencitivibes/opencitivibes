"""Add email login codes table for passwordless authentication.

Revision ID: 72bf99112cc1
Revises: 61ae9a36500a
Create Date: 2025-12-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "72bf99112cc1"
down_revision: Union[str, None] = "61ae9a36500a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_login_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_login_codes_id", "email_login_codes", ["id"])
    op.create_index(
        "ix_email_login_codes_user_created",
        "email_login_codes",
        ["user_id", "created_at"],
    )
    op.create_index("ix_email_login_codes_expires", "email_login_codes", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_email_login_codes_expires", "email_login_codes")
    op.drop_index("ix_email_login_codes_user_created", "email_login_codes")
    op.drop_index("ix_email_login_codes_id", "email_login_codes")
    op.drop_table("email_login_codes")
