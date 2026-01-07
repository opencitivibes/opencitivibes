"""add_login_events_table
Revision ID: 04dd2ce31e3f
Revises: e8gk77h64i9f
Create Date: 2026-01-07 03:11:37
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "04dd2ce31e3f"
down_revision = "e8gk77h64i9f"
branch_labels = None
depends_on = None


def upgrade():
    # Create login_events table for security audit tracking
    op.create_table(
        "login_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=True,
            comment="User who triggered the event (null for failed login with unknown user)",
        ),
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=True,
            comment="Email used in login attempt (stored even if user not found)",
        ),
        sa.Column(
            "event_type",
            sa.Enum(
                "LOGIN_SUCCESS",
                "LOGIN_FAILED",
                "LOGOUT",
                "PASSWORD_RESET_REQUEST",
                name="logineventtype",
            ),
            nullable=False,
            comment="Type of login event",
        ),
        sa.Column(
            "ip_address",
            sa.String(length=45),
            nullable=True,
            comment="Client IP address (IPv6 max length)",
        ),
        sa.Column(
            "user_agent",
            sa.Text(),
            nullable=True,
            comment="Browser/client user agent string",
        ),
        sa.Column(
            "failure_reason",
            sa.Enum(
                "INVALID_PASSWORD",
                "USER_NOT_FOUND",
                "ACCOUNT_INACTIVE",
                "RATE_LIMITED",
                "TWO_FACTOR_FAILED",
                "ACCOUNT_BANNED",
                name="loginfailurereason",
            ),
            nullable=True,
            comment="Reason for login failure (null for success/logout)",
        ),
        sa.Column(
            "metadata_json",
            sa.Text(),
            nullable=True,
            comment="JSON with additional event details (2FA method, etc.)",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_login_events_created_at"), "login_events", ["created_at"], unique=False
    )
    op.create_index(
        "ix_login_events_event_type", "login_events", ["event_type"], unique=False
    )
    op.create_index(
        "ix_login_events_ip_address", "login_events", ["ip_address"], unique=False
    )
    op.create_index(
        "ix_login_events_user_id", "login_events", ["user_id"], unique=False
    )


def downgrade():
    # Drop login_events table and indexes
    op.drop_index("ix_login_events_user_id", table_name="login_events")
    op.drop_index("ix_login_events_ip_address", table_name="login_events")
    op.drop_index("ix_login_events_event_type", table_name="login_events")
    op.drop_index(op.f("ix_login_events_created_at"), table_name="login_events")
    op.drop_table("login_events")
