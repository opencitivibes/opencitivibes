"""Add official role to users

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-12-29

Adds official role system to users:
- Official status fields (granted by admin): is_official, official_title, official_verified_at
- Official request fields (from signup): requests_official_status, official_title_request, official_request_at
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add official role columns to users table."""
    # Add official status columns (granted by admin)
    op.add_column(
        "users",
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("official_title", sa.String(100), nullable=True))
    op.add_column(
        "users", sa.Column("official_verified_at", sa.DateTime(), nullable=True)
    )

    # Add official request columns (from signup - pending approval)
    op.add_column(
        "users",
        sa.Column(
            "requests_official_status", sa.Boolean(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "users", sa.Column("official_title_request", sa.String(100), nullable=True)
    )
    op.add_column(
        "users", sa.Column("official_request_at", sa.DateTime(), nullable=True)
    )

    # Remove server_defaults after columns are added (cleaner model)
    op.alter_column("users", "is_official", server_default=None)
    op.alter_column("users", "requests_official_status", server_default=None)


def downgrade() -> None:
    """Remove official role columns from users table."""
    # Drop request columns
    op.drop_column("users", "official_request_at")
    op.drop_column("users", "official_title_request")
    op.drop_column("users", "requests_official_status")

    # Drop status columns
    op.drop_column("users", "official_verified_at")
    op.drop_column("users", "official_title")
    op.drop_column("users", "is_official")
