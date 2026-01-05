"""
Database configuration with connection pooling.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from models.config import settings


def create_db_engine():
    """
    Create database engine with appropriate configuration.

    Uses QueuePool for PostgreSQL/production and NullPool for SQLite.
    NullPool creates a new connection per request, avoiding concurrency issues.
    """
    is_sqlite = "sqlite" in settings.DATABASE_URL

    if is_sqlite:
        # SQLite with NullPool: creates new connection per request
        # This avoids the race conditions that occur with StaticPool under concurrency
        return create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
        )
    else:
        # PostgreSQL or other databases: use QueuePool with tuned settings
        return create_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=True,  # Verify connections before use
        )


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Get database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
