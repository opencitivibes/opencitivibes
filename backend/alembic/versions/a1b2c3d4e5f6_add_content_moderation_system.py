"""Add content moderation system

Revision ID: a1b2c3d4e5f6
Revises: 87d33473f8b1
Create Date: 2025-12-27

Adds database tables and columns for the content moderation system:
- New enums: FlagReason, FlagStatus, ContentType, PenaltyType, PenaltyStatus, AppealStatus
- New tables: content_flags, user_penalties, appeals, keyword_watchlist, admin_notes
- New columns on users: trust_score, approved_comments_count, total_flags_received,
  valid_flags_received, flags_submitted_validated, requires_comment_approval
- New columns on comments: deleted_at, deleted_by, deletion_reason, is_hidden, hidden_at,
  flag_count, requires_approval, approved_at, approved_by
- New columns on ideas: is_hidden, hidden_at, flag_count
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "87d33473f8b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create content moderation schema."""
    # Create enums (SQLite stores as strings, no native enum type)
    # The Python Enum classes handle validation

    # Create content_flags table
    op.create_table(
        "content_flags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_type", "content_id", "reporter_id", name="uq_flag_content_reporter"
        ),
    )
    op.create_index(
        "ix_content_flags_content", "content_flags", ["content_type", "content_id"]
    )
    op.create_index("ix_content_flags_status", "content_flags", ["status"])
    op.create_index("ix_content_flags_reporter", "content_flags", ["reporter_id"])
    op.create_index("ix_content_flags_id", "content_flags", ["id"])

    # Create user_penalties table
    op.create_table(
        "user_penalties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("penalty_type", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("issued_by", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by", sa.Integer(), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column("related_flag_ids", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["issued_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_penalties_user_status", "user_penalties", ["user_id", "status"]
    )
    op.create_index("ix_user_penalties_expires", "user_penalties", ["expires_at"])
    op.create_index("ix_user_penalties_type", "user_penalties", ["penalty_type"])
    op.create_index("ix_user_penalties_id", "user_penalties", ["id"])

    # Create appeals table
    op.create_table(
        "appeals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("penalty_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["penalty_id"],
            ["user_penalties.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("penalty_id", name="uq_appeal_penalty"),
    )
    op.create_index("ix_appeals_status", "appeals", ["status"])
    op.create_index("ix_appeals_user", "appeals", ["user_id"])
    op.create_index("ix_appeals_id", "appeals", ["id"])

    # Create keyword_watchlist table
    op.create_table(
        "keyword_watchlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("keyword", sa.String(100), nullable=False),
        sa.Column("is_regex", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "auto_flag_reason", sa.String(50), nullable=False, server_default="spam"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("match_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keyword", name="uq_keyword"),
    )
    op.create_index("ix_keyword_watchlist_keyword", "keyword_watchlist", ["keyword"])
    op.create_index("ix_keyword_watchlist_id", "keyword_watchlist", ["id"])

    # Create admin_notes table
    op.create_table(
        "admin_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_notes_user", "admin_notes", ["user_id"])
    op.create_index("ix_admin_notes_id", "admin_notes", ["id"])

    # Add columns to users table
    op.add_column(
        "users",
        sa.Column("trust_score", sa.Integer(), nullable=False, server_default="50"),
    )
    op.add_column(
        "users",
        sa.Column(
            "approved_comments_count", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "total_flags_received", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "valid_flags_received", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "flags_submitted_validated",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "requires_comment_approval",
            sa.Boolean(),
            nullable=False,
            server_default="1",
        ),
    )

    # Add columns to comments table
    op.add_column("comments", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("comments", sa.Column("deleted_by", sa.Integer(), nullable=True))
    op.add_column("comments", sa.Column("deletion_reason", sa.Text(), nullable=True))
    op.add_column(
        "comments",
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("comments", sa.Column("hidden_at", sa.DateTime(), nullable=True))
    op.add_column(
        "comments",
        sa.Column("flag_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "comments",
        sa.Column(
            "requires_approval", sa.Boolean(), nullable=False, server_default="0"
        ),
    )
    op.add_column("comments", sa.Column("approved_at", sa.DateTime(), nullable=True))
    op.add_column("comments", sa.Column("approved_by", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_comments_deleted_by", "comments", "users", ["deleted_by"], ["id"]
    )
    op.create_foreign_key(
        "fk_comments_approved_by", "comments", "users", ["approved_by"], ["id"]
    )
    op.create_index("ix_comments_hidden", "comments", ["is_hidden"])
    op.create_index("ix_comments_requires_approval", "comments", ["requires_approval"])
    op.create_index("ix_comments_deleted", "comments", ["deleted_at"])

    # Add columns to ideas table
    op.add_column(
        "ideas",
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("ideas", sa.Column("hidden_at", sa.DateTime(), nullable=True))
    op.add_column(
        "ideas",
        sa.Column("flag_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_ideas_hidden", "ideas", ["is_hidden"])


def downgrade() -> None:
    """Remove content moderation schema."""
    # Remove indexes from ideas
    op.drop_index("ix_ideas_hidden", table_name="ideas")

    # Remove columns from ideas
    op.drop_column("ideas", "flag_count")
    op.drop_column("ideas", "hidden_at")
    op.drop_column("ideas", "is_hidden")

    # Remove indexes from comments
    op.drop_index("ix_comments_deleted", table_name="comments")
    op.drop_index("ix_comments_requires_approval", table_name="comments")
    op.drop_index("ix_comments_hidden", table_name="comments")

    # Remove foreign keys from comments
    op.drop_constraint("fk_comments_approved_by", "comments", type_="foreignkey")
    op.drop_constraint("fk_comments_deleted_by", "comments", type_="foreignkey")

    # Remove columns from comments
    op.drop_column("comments", "approved_by")
    op.drop_column("comments", "approved_at")
    op.drop_column("comments", "requires_approval")
    op.drop_column("comments", "flag_count")
    op.drop_column("comments", "hidden_at")
    op.drop_column("comments", "is_hidden")
    op.drop_column("comments", "deletion_reason")
    op.drop_column("comments", "deleted_by")
    op.drop_column("comments", "deleted_at")

    # Remove columns from users
    op.drop_column("users", "requires_comment_approval")
    op.drop_column("users", "flags_submitted_validated")
    op.drop_column("users", "valid_flags_received")
    op.drop_column("users", "total_flags_received")
    op.drop_column("users", "approved_comments_count")
    op.drop_column("users", "trust_score")

    # Drop tables
    op.drop_index("ix_admin_notes_id", table_name="admin_notes")
    op.drop_index("ix_admin_notes_user", table_name="admin_notes")
    op.drop_table("admin_notes")

    op.drop_index("ix_keyword_watchlist_id", table_name="keyword_watchlist")
    op.drop_index("ix_keyword_watchlist_keyword", table_name="keyword_watchlist")
    op.drop_table("keyword_watchlist")

    op.drop_index("ix_appeals_id", table_name="appeals")
    op.drop_index("ix_appeals_user", table_name="appeals")
    op.drop_index("ix_appeals_status", table_name="appeals")
    op.drop_table("appeals")

    op.drop_index("ix_user_penalties_id", table_name="user_penalties")
    op.drop_index("ix_user_penalties_type", table_name="user_penalties")
    op.drop_index("ix_user_penalties_expires", table_name="user_penalties")
    op.drop_index("ix_user_penalties_user_status", table_name="user_penalties")
    op.drop_table("user_penalties")

    op.drop_index("ix_content_flags_id", table_name="content_flags")
    op.drop_index("ix_content_flags_reporter", table_name="content_flags")
    op.drop_index("ix_content_flags_status", table_name="content_flags")
    op.drop_index("ix_content_flags_content", table_name="content_flags")
    op.drop_table("content_flags")
