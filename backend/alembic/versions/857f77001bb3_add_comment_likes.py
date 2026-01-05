"""add_comment_likes

Revision ID: 857f77001bb3
Revises: c3d4e5f6g7h8
Create Date: 2025-12-30 15:14:30
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "857f77001bb3"
down_revision = "c3d4e5f6g7h8"
branch_labels = None
depends_on = None


def upgrade():
    # Create comment_likes table
    op.create_table(
        "comment_likes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "comment_id", "user_id", name="uq_comment_like_comment_user"
        ),
    )
    op.create_index("ix_comment_likes_id", "comment_likes", ["id"], unique=False)
    op.create_index(
        "ix_comment_likes_comment", "comment_likes", ["comment_id"], unique=False
    )
    op.create_index("ix_comment_likes_user", "comment_likes", ["user_id"], unique=False)

    # Add like_count column to comments table
    op.add_column(
        "comments",
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    # Remove like_count column from comments
    op.drop_column("comments", "like_count")

    # Drop comment_likes table
    op.drop_index("ix_comment_likes_user", table_name="comment_likes")
    op.drop_index("ix_comment_likes_comment", table_name="comment_likes")
    op.drop_index("ix_comment_likes_id", table_name="comment_likes")
    op.drop_table("comment_likes")
