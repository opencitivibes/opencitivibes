"""initial

Revision ID: 0001_initial
Revises:
Create Date: 2025-12-26 00:00:00.000000

This is a convenience initial migration that creates the database schema
based on the SQLAlchemy `Base` metadata. It is safe to use as an initial
migration in a new project or test environment. For production, prefer
an autogenerate-based migration or hand-crafted migrations that capture
intended schema evolution and data migrations.
"""

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables declared on Base.metadata."""
    # Import app metadata and engine so migrations run with the same metadata
    from repositories.database import Base, engine

    Base.metadata.create_all(bind=engine)


def downgrade() -> None:
    """Drop all tables declared on Base.metadata.

    WARNING: This will drop all tables and result in data loss. Use only in
    development/test environments or when you're certain.
    """
    from repositories.database import Base, engine

    Base.metadata.drop_all(bind=engine)
