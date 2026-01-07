"""
Diagnostics service for system health checks.

Provides database connectivity diagnostics, table statistics,
connection pool information, and system resource monitoring.
"""

import re

from loguru import logger
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import Pool

from models.config import settings
from models.schemas import (
    DatabaseDiagnosticsResponse,
    DatabaseSizeInfo,
    DiskUsageInfo,
    DockerUsageInfo,
    PoolInfo,
    SystemResourcesResponse,
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
                    text(f'SELECT COUNT(*) FROM "{table_name}"')  # noqa: S608 # nosec B608 # nosemgrep
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

    @staticmethod
    def get_system_resources(db: Session) -> SystemResourcesResponse:
        """
        Get system resource usage including disk, Docker, and database size.

        Args:
            db: Database session for database size queries

        Returns:
            SystemResourcesResponse with disk, docker, database metrics
        """

        error: str | None = None
        disk_info: DiskUsageInfo | None = None
        docker_info: DockerUsageInfo | None = None
        db_size_info: DatabaseSizeInfo | None = None
        uptime_seconds: int | None = None
        load_average: list[float] | None = None
        memory_percent: float | None = None

        try:
            # Disk usage - check root filesystem
            disk_info = DiagnosticsService._get_disk_usage()
        except Exception as e:
            logger.warning(f"Failed to get disk usage: {e}")

        try:
            # Docker usage
            docker_info = DiagnosticsService._get_docker_usage()
        except Exception as e:
            logger.warning(f"Failed to get Docker usage: {e}")

        try:
            # Database size
            db_url = settings.DATABASE_URL
            db_type = DiagnosticsService._detect_database_type(db_url)
            db_size_info = DiagnosticsService._get_database_size(db, db_type, db_url)
        except Exception as e:
            logger.warning(f"Failed to get database size: {e}")

        try:
            # System uptime and load
            uptime_seconds = DiagnosticsService._get_uptime()
            load_average = DiagnosticsService._get_load_average()
            memory_percent = DiagnosticsService._get_memory_usage()
        except Exception as e:
            logger.warning(f"Failed to get system metrics: {e}")

        return SystemResourcesResponse(
            disk=disk_info,
            docker=docker_info,
            database_size=db_size_info,
            uptime_seconds=uptime_seconds,
            load_average=load_average,
            memory_used_percent=memory_percent,
            error=error,
        )

    @staticmethod
    def _get_disk_usage() -> DiskUsageInfo:
        """Get disk usage for the root filesystem."""
        import shutil

        usage = shutil.disk_usage("/")
        return DiskUsageInfo(
            total_gb=round(usage.total / (1024**3), 2),
            used_gb=round(usage.used / (1024**3), 2),
            free_gb=round(usage.free / (1024**3), 2),
            used_percent=round((usage.used / usage.total) * 100, 1),
        )

    @staticmethod
    def _get_docker_usage() -> DockerUsageInfo | None:
        """Get Docker disk usage by parsing 'docker system df' output."""
        import subprocess

        try:
            # Run docker system df with parseable format
            result = subprocess.run(  # noqa: S603 S607
                [
                    "docker",
                    "system",
                    "df",
                    "--format",
                    "{{.Type}}\t{{.Size}}\t{{.Reclaimable}}",
                ],  # noqa: S603 S607
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.warning(f"Docker command failed: {result.stderr}")
                return None

            # Parse output
            images_size = 0.0
            images_reclaim = 0.0
            containers_size = 0.0
            volumes_size = 0.0
            build_cache = 0.0
            build_cache_reclaim = 0.0

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 3:
                    type_name = parts[0].lower()
                    size = DiagnosticsService._parse_docker_size(parts[1])
                    reclaim = DiagnosticsService._parse_docker_size(
                        parts[2].split()[0] if parts[2] else "0"
                    )

                    if "image" in type_name:
                        images_size = size
                        images_reclaim = reclaim
                    elif "container" in type_name:
                        containers_size = size
                    elif "volume" in type_name:
                        volumes_size = size
                    elif "build" in type_name:
                        build_cache = size
                        build_cache_reclaim = reclaim

            return DockerUsageInfo(
                images_size_gb=round(images_size / (1024**3), 2),
                images_reclaimable_gb=round(images_reclaim / (1024**3), 2),
                containers_size_mb=round(containers_size / (1024**2), 1),
                volumes_size_mb=round(volumes_size / (1024**2), 1),
                build_cache_gb=round(build_cache / (1024**3), 2),
                build_cache_reclaimable_gb=round(build_cache_reclaim / (1024**3), 2),
            )

        except subprocess.TimeoutExpired:
            logger.warning("Docker command timed out")
            return None
        except FileNotFoundError:
            logger.info("Docker not available on this system")
            return None

    @staticmethod
    def _parse_docker_size(size_str: str) -> float:
        """Parse Docker size string (e.g., '1.5GB', '500MB') to bytes."""
        size_str = size_str.strip().upper()
        if not size_str or size_str == "0B" or size_str == "0":
            return 0.0

        multipliers = {
            "B": 1,
            "KB": 1024,
            "MB": 1024**2,
            "GB": 1024**3,
            "TB": 1024**4,
        }

        for suffix, mult in multipliers.items():
            if size_str.endswith(suffix):
                try:
                    return float(size_str[: -len(suffix)]) * mult
                except ValueError:
                    return 0.0

        return 0.0

    @staticmethod
    def _get_database_size(
        db: Session, db_type: str, db_url: str
    ) -> DatabaseSizeInfo | None:
        """Get database size based on database type."""
        import os

        if db_type == "sqlite":
            # Extract file path from SQLite URL
            # Format: sqlite:///./data/database.db or sqlite:////absolute/path.db
            path = db_url.replace("sqlite:///", "")
            if path.startswith("./"):
                # Relative path - resolve from working directory
                path = os.path.abspath(path)

            if os.path.exists(path):
                size_bytes = os.path.getsize(path)
                return DatabaseSizeInfo(
                    database_type="sqlite",
                    size_mb=round(size_bytes / (1024**2), 2),
                    file_path=os.path.basename(path),
                )
            return None

        elif db_type == "postgresql":
            # Query PostgreSQL for database size
            try:
                result = db.execute(text("SELECT pg_database_size(current_database())"))
                size_bytes = result.scalar()
                if size_bytes:
                    return DatabaseSizeInfo(
                        database_type="postgresql",
                        size_mb=round(size_bytes / (1024**2), 2),
                    )
            except Exception as e:
                logger.warning(f"Failed to query PostgreSQL size: {e}")

        return None

    @staticmethod
    def _get_uptime() -> int | None:
        """Get system uptime in seconds."""
        import os

        try:
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime") as f:  # noqa: PTH123
                    return int(float(f.read().split()[0]))
        except Exception:
            pass
        return None

    @staticmethod
    def _get_load_average() -> list[float] | None:
        """Get system load average (1, 5, 15 minutes)."""
        import os

        try:
            load = os.getloadavg()
            return [round(x, 2) for x in load]
        except (OSError, AttributeError):
            # Not available on Windows
            return None

    @staticmethod
    def _get_memory_usage() -> float | None:
        """Get memory usage percentage from /proc/meminfo."""
        try:
            with open("/proc/meminfo") as f:  # noqa: PTH123
                lines = f.readlines()

            mem_total = 0
            mem_available = 0

            for line in lines:
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    mem_available = int(line.split()[1])

            if mem_total > 0:
                used = mem_total - mem_available
                return round((used / mem_total) * 100, 1)
        except Exception:
            pass
        return None
