"""add_parental_consent_law25

Revision ID: 0347f796d25b
Revises: g0im99j86k1h
Create Date: 2026-01-11 20:40:56

Law 25 Minors Compliance: Add parental consent tracking for users under 14.
- Add User fields: date_of_birth, is_minor, requires_parental_consent, parent_email,
  parental_consent_status, parental_consent_granted_at, parental_consent_proof_id
- Create parental_consent_tokens table for consent verification
- Create parental_consent_logs table for audit trail
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0347f796d25b"
down_revision = "g0im99j86k1h"
branch_labels = None
depends_on = None


def upgrade():
    # Add User model fields for Law 25 minors compliance
    op.add_column(
        "users",
        sa.Column(
            "date_of_birth",
            sa.DateTime(),
            nullable=True,
            comment="User date of birth for age verification (Law 25)",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_minor",
            sa.Boolean(),
            nullable=False,
            server_default="0",
            comment="True if user was under 14 at registration",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "requires_parental_consent",
            sa.Boolean(),
            nullable=False,
            server_default="0",
            comment="True if user required parental consent at registration",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "parent_email",
            sa.String(length=255),
            nullable=True,
            comment="Parent/guardian email for consent (minors only)",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "parental_consent_status",
            sa.String(length=20),
            nullable=False,
            server_default="not_required",
            comment="Status: not_required, pending, granted, denied, expired",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "parental_consent_granted_at",
            sa.DateTime(),
            nullable=True,
            comment="When parent granted consent",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "parental_consent_proof_id",
            sa.String(length=64),
            nullable=True,
            comment="Reference to consent proof document/record",
        ),
    )
    op.create_index(
        op.f("ix_users_parent_email"), "users", ["parent_email"], unique=False
    )

    # Create parental_consent_tokens table
    op.create_table(
        "parental_consent_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "pending_user_id",
            sa.Integer(),
            nullable=False,
            comment="User awaiting parental consent",
        ),
        sa.Column(
            "token_hash",
            sa.String(length=64),
            nullable=False,
            comment="SHA-256 hash of the consent token",
        ),
        sa.Column(
            "parent_email",
            sa.String(length=255),
            nullable=False,
            comment="Parent/guardian email for consent request",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(),
            nullable=False,
            comment="Token expiration (default 7 days)",
        ),
        sa.Column(
            "used_at",
            sa.DateTime(),
            nullable=True,
            comment="When the token was used to grant/deny consent",
        ),
        sa.Column(
            "consent_decision",
            sa.String(length=20),
            nullable=True,
            comment="Parent decision: granted, denied (null if unused)",
        ),
        sa.Column(
            "ip_address",
            sa.String(length=45),
            nullable=True,
            comment="IP address when consent was given/denied",
        ),
        sa.Column(
            "user_agent",
            sa.String(length=500),
            nullable=True,
            comment="User agent when consent was given/denied",
        ),
        sa.ForeignKeyConstraint(["pending_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_parental_consent_tokens_id"),
        "parental_consent_tokens",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_parental_consent_tokens_pending_user_id"),
        "parental_consent_tokens",
        ["pending_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_parental_consent_tokens_user_created",
        "parental_consent_tokens",
        ["pending_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_parental_consent_tokens_expires",
        "parental_consent_tokens",
        ["expires_at"],
        unique=False,
    )

    # Create parental_consent_logs table
    op.create_table(
        "parental_consent_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
            comment="User this log entry relates to",
        ),
        sa.Column(
            "action",
            sa.String(length=50),
            nullable=False,
            comment="Action: request_sent, consent_granted, consent_denied, consent_expired",
        ),
        sa.Column(
            "parent_email",
            sa.String(length=255),
            nullable=False,
            comment="Parent/guardian email at time of action",
        ),
        sa.Column(
            "token_id",
            sa.Integer(),
            nullable=True,
            comment="Related consent token (if applicable)",
        ),
        sa.Column(
            "ip_address",
            sa.String(length=45),
            nullable=True,
            comment="IP address when action occurred",
        ),
        sa.Column(
            "user_agent",
            sa.String(length=500),
            nullable=True,
            comment="User agent when action occurred",
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            comment="Additional notes about the action",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["token_id"], ["parental_consent_tokens.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_parental_consent_logs_id"),
        "parental_consent_logs",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_parental_consent_logs_user_id",
        "parental_consent_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_parental_consent_logs_created_at",
        "parental_consent_logs",
        ["created_at"],
        unique=False,
    )


def downgrade():
    # Drop parental_consent_logs table
    op.drop_index(
        "ix_parental_consent_logs_created_at", table_name="parental_consent_logs"
    )
    op.drop_index(
        "ix_parental_consent_logs_user_id", table_name="parental_consent_logs"
    )
    op.drop_index(
        op.f("ix_parental_consent_logs_id"), table_name="parental_consent_logs"
    )
    op.drop_table("parental_consent_logs")

    # Drop parental_consent_tokens table
    op.drop_index(
        "ix_parental_consent_tokens_expires", table_name="parental_consent_tokens"
    )
    op.drop_index(
        "ix_parental_consent_tokens_user_created",
        table_name="parental_consent_tokens",
    )
    op.drop_index(
        op.f("ix_parental_consent_tokens_pending_user_id"),
        table_name="parental_consent_tokens",
    )
    op.drop_index(
        op.f("ix_parental_consent_tokens_id"), table_name="parental_consent_tokens"
    )
    op.drop_table("parental_consent_tokens")

    # Remove User columns
    op.drop_index(op.f("ix_users_parent_email"), table_name="users")
    op.drop_column("users", "parental_consent_proof_id")
    op.drop_column("users", "parental_consent_granted_at")
    op.drop_column("users", "parental_consent_status")
    op.drop_column("users", "parent_email")
    op.drop_column("users", "requires_parental_consent")
    op.drop_column("users", "is_minor")
    op.drop_column("users", "date_of_birth")
