"""Add vote qualities system

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-28

Adds vote qualities system:
- New enum: StakeholderType
- New tables: qualities, category_qualities, vote_qualities
- New columns on votes: voter_neighborhood, stakeholder_type
- Seed data for 4 default qualities
"""

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Seed data for default qualities
DEFAULT_QUALITIES = [
    {
        "key": "community_benefit",
        "name_en": "Benefits everyone",
        "name_fr": "Bénéficie à tous",
        "description_en": "This idea would help the broader community",
        "description_fr": "Cette idée aiderait la communauté en général",
        "icon": "heart",
        "color": "rose",
        "is_default": True,
        "display_order": 1,
    },
    {
        "key": "quality_of_life",
        "name_en": "Improves daily life",
        "name_fr": "Améliore le quotidien",
        "description_en": "This would make day-to-day life better",
        "description_fr": "Cela améliorerait la vie au quotidien",
        "icon": "sun",
        "color": "amber",
        "is_default": True,
        "display_order": 2,
    },
    {
        "key": "urgent",
        "name_en": "Addresses urgent problem",
        "name_fr": "Problème urgent",
        "description_en": "This solves a pressing issue that needs attention",
        "description_fr": "Cela résout un problème pressant",
        "icon": "alert-triangle",
        "color": "red",
        "is_default": True,
        "display_order": 3,
    },
    {
        "key": "would_volunteer",
        "name_en": "I'd help make this happen",
        "name_fr": "Je participerais",
        "description_en": "I would volunteer my time to help implement this",
        "description_fr": "Je donnerais de mon temps pour aider à réaliser ceci",
        "icon": "hand-helping",
        "color": "emerald",
        "is_default": True,
        "display_order": 4,
    },
]


def upgrade() -> None:
    """Create vote qualities schema and seed data."""
    # Create qualities table
    op.create_table(
        "qualities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(50), nullable=False),
        sa.Column("name_en", sa.String(100), nullable=False),
        sa.Column("name_fr", sa.String(100), nullable=False),
        sa.Column("description_en", sa.String(255), nullable=True),
        sa.Column("description_fr", sa.String(255), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("color", sa.String(30), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_qualities_id", "qualities", ["id"])
    op.create_index("ix_qualities_is_default", "qualities", ["is_default"])

    # Create category_qualities table
    op.create_table(
        "category_qualities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("quality_id", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("display_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quality_id"], ["qualities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category_id", "quality_id", name="uq_category_quality"),
    )
    op.create_index("ix_category_qualities_id", "category_qualities", ["id"])
    op.create_index(
        "ix_category_qualities_category", "category_qualities", ["category_id"]
    )

    # Create vote_qualities table
    op.create_table(
        "vote_qualities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vote_id", sa.Integer(), nullable=False),
        sa.Column("quality_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["vote_id"], ["votes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quality_id"], ["qualities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vote_id", "quality_id", name="uq_vote_quality"),
    )
    op.create_index("ix_vote_qualities_id", "vote_qualities", ["id"])
    op.create_index("ix_vote_qualities_vote", "vote_qualities", ["vote_id"])
    op.create_index("ix_vote_qualities_quality", "vote_qualities", ["quality_id"])

    # Add future-proofing columns to votes table
    # Using String for stakeholder_type (SQLite doesn't support native enum)
    op.add_column(
        "votes", sa.Column("voter_neighborhood", sa.String(100), nullable=True)
    )
    op.add_column("votes", sa.Column("stakeholder_type", sa.String(50), nullable=True))

    # Seed default qualities
    qualities_table = sa.table(
        "qualities",
        sa.column("key", sa.String),
        sa.column("name_en", sa.String),
        sa.column("name_fr", sa.String),
        sa.column("description_en", sa.String),
        sa.column("description_fr", sa.String),
        sa.column("icon", sa.String),
        sa.column("color", sa.String),
        sa.column("is_default", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("display_order", sa.Integer),
        sa.column("created_at", sa.DateTime),
    )

    now = datetime.now(timezone.utc)
    for quality in DEFAULT_QUALITIES:
        op.execute(
            qualities_table.insert().values(
                **quality,
                is_active=True,
                created_at=now,
            )
        )


def downgrade() -> None:
    """Remove vote qualities schema."""
    # Remove future-proofing columns from votes
    op.drop_column("votes", "stakeholder_type")
    op.drop_column("votes", "voter_neighborhood")

    # Drop quality tables
    op.drop_index("ix_vote_qualities_quality", table_name="vote_qualities")
    op.drop_index("ix_vote_qualities_vote", table_name="vote_qualities")
    op.drop_index("ix_vote_qualities_id", table_name="vote_qualities")
    op.drop_table("vote_qualities")

    op.drop_index("ix_category_qualities_category", table_name="category_qualities")
    op.drop_index("ix_category_qualities_id", table_name="category_qualities")
    op.drop_table("category_qualities")

    op.drop_index("ix_qualities_is_default", table_name="qualities")
    op.drop_index("ix_qualities_id", table_name="qualities")
    op.drop_table("qualities")
