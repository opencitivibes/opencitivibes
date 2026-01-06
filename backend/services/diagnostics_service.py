"""
Diagnostics service for system health checks.

Provides database connectivity diagnostics, table statistics,
and connection pool information.
"""

import re

from loguru import logger
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import Pool

from models.config import settings
from models.schemas import (
    DatabaseDiagnosticsResponse,
    PoolInfo,
    TableInfo,
)
from repositories.database import engine


class DiagnosticsService:
    """Service for system diagnostics operations."""

    @staticmethod
    def get_database_diagnostics(db: Session) -> DatabaseDiagnosticsResponse:
        """
        Get database connectivity and table information.

        Args:
            db: Database session

        Returns:
            DatabaseDiagnosticsResponse containing:
            - connected: Whether database is reachable
            - database_type: "sqlite", "postgresql", or "other"
            - database_url_masked: Masked connection string for security
            - tables: List of tables with row counts
            - pool_info: Connection pool statistics (PostgreSQL only)
            - error: Error message if connection failed
        """
        connected = False
        database_type = "unknown"
        database_url_masked = ""
        tables: list[TableInfo] = []
        pool_info: PoolInfo | None = None
        error: str | None = None

        try:
            # Detect database type
            db_url = settings.DATABASE_URL
            database_type = DiagnosticsService._detect_database_type(db_url)
            database_url_masked = DiagnosticsService._mask_database_url(
                db_url, database_type
            )

            # Test connectivity with a simple query
            db.execute(text("SELECT 1"))
            connected = True

            # Get table information using inspector
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            tables = DiagnosticsService._get_table_statistics(db, table_names)

            # Get connection pool info for PostgreSQL
            if database_type == "postgresql":
                pool_info = DiagnosticsService._get_pool_info(engine.pool)

        except Exception as e:
            logger.warning(f"Database diagnostics failed: {e}")
            error = str(e)

        return DatabaseDiagnosticsResponse(
            connected=connected,
            database_type=database_type,
            database_url_masked=database_url_masked,
            tables=tables,
            pool_info=pool_info,
            error=error,
        )

    @staticmethod
    def _detect_database_type(db_url: str) -> str:
        """Detect the database type from connection URL."""
        if "sqlite" in db_url:
            return "sqlite"
        elif "postgresql" in db_url:
            return "postgresql"
        return "other"

    @staticmethod
    def _mask_database_url(db_url: str, db_type: str) -> str:
        """Mask sensitive parts of the database URL."""
        if db_type == "sqlite":
            # Show only the filename
            return "sqlite:///.../" + db_url.split("/")[-1]
        elif db_type == "postgresql":
            # Show only the host
            match = re.search(r"@([^/]+)/", db_url)
            if match:
                return f"postgresql://***@{match.group(1)}/***"
            return "postgresql://***"
        return "***"

    @staticmethod
    def _get_table_statistics(db: Session, table_names: list[str]) -> list[TableInfo]:
        """Get row counts for each table using safe parameterized queries."""
        tables_info: list[TableInfo] = []

        for table_name in sorted(table_names):
            try:
                # Use text() with a safe identifier check
                # Table names from inspector.get_table_names() are trusted
                # But we validate the format for extra safety
                if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
                    logger.warning(f"Skipping table with unusual name: {table_name}")
                    continue

                # SQLite and PostgreSQL both support this syntax safely
                # The table name has been validated above
                count_result = db.execute(
                    text(f'SELECT COUNT(*) FROM "{table_name}"')  # noqa: S608 # nosec B608
                )
                row_count = count_result.scalar()
                tables_info.append(TableInfo(name=table_name, row_count=row_count))
            except Exception as e:
                logger.warning(f"Failed to count rows for table {table_name}: {e}")
                tables_info.append(TableInfo(name=table_name, row_count=None))

        return tables_info

    @staticmethod
    def _get_pool_info(pool: Pool) -> PoolInfo:
        """Get connection pool statistics safely."""
        # Use getattr to safely access pool methods that may vary by pool type
        return PoolInfo(
            pool_size=getattr(pool, "size", None),
            checked_in=getattr(pool, "checkedin", lambda: 0)(),
            checked_out=getattr(pool, "checkedout", lambda: 0)(),
            overflow=getattr(pool, "overflow", lambda: 0)(),
            invalid=(
                getattr(pool, "invalidatedcount", lambda: None)()
                if hasattr(pool, "invalidatedcount")
                else None
            ),
        )
