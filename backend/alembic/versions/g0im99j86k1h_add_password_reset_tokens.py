"""Add password reset tokens table with bcrypt hashing (Security Audit Phase 1).

Security features:
- Finding #1 (CRITICAL): Uses bcrypt (60 chars) instead of SHA-256
- Finding #4 (HIGH): Tracks attempts for account lockout
- Finding #11 (LOW): Context signature binding via HMAC

Revision ID: g0im99j86k1h
Revises: f9hl88i75j0g
Create Date: 2026-01-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g0im99j86k1h"
down_revision: Union[str, None] = "f9hl88i75j0g"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        # Primary key
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        # Bcrypt hash of reset code (60 chars for bcrypt - Finding #1)
        sa.Column(
            "code_hash",
            sa.String(60),
            nullable=False,
            comment="bcrypt hash of reset code (NOT SHA-256 - Finding #1)",
        ),
        # Phase 1: Code verification
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(),
            nullable=False,
            comment="Code expiry timestamp",
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Code verification attempts (Finding #2)",
        ),
        sa.Column(
            "verified_at",
            sa.DateTime(),
            nullable=True,
            comment="When code was successfully verified",
        ),
        # Phase 2: Reset token (issued after code verification)
        sa.Column(
            "reset_token",
            sa.String(64),
            nullable=True,
            unique=True,
            comment="Token for password reset (issued after code verified)",
        ),
        sa.Column(
            "reset_token_expires_at",
            sa.DateTime(),
            nullable=True,
            comment="Reset token expiry",
        ),
        sa.Column(
            "reset_token_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Reset token usage attempts",
        ),
        # Phase 3: Completion tracking
        sa.Column(
            "used_at",
            sa.DateTime(),
            nullable=True,
            comment="When password was successfully reset",
        ),
        # Context binding (Finding #11)
        sa.Column(
            "context_signature",
            sa.String(64),
            nullable=True,
            comment="HMAC signature binding token to user context (Finding #11)",
        ),
        # Audit logging (Finding #9)
        sa.Column(
            "ip_address",
            sa.String(45),
            nullable=True,
            comment="IP address when code was requested",
        ),
        sa.Column(
            "user_agent",
            sa.String(500),
            nullable=True,
            comment="User agent for audit logging (Finding #9)",
        ),
        # Constraints
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_password_reset_tokens_id", "password_reset_tokens", ["id"])
    op.create_index(
        "ix_password_reset_tokens_user_created",
        "password_reset_tokens",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_password_reset_tokens_expires",
        "password_reset_tokens",
        ["expires_at"],
    )
    op.create_index(
        "ix_password_reset_tokens_reset_token",
        "password_reset_tokens",
        ["reset_token"],
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_reset_token", "password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_expires", "password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_created", "password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_id", "password_reset_tokens")
    op.drop_table("password_reset_tokens")
