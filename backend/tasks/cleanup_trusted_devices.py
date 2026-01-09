#!/usr/bin/env python3
"""
Cleanup task for trusted devices.

Law 25 Compliance: Data Retention
- Expired devices are soft-deleted immediately
- Revoked devices are permanently deleted after retention period

This script can be run:
- Via cron: 0 * * * * cd /path/to/backend && python -m tasks.cleanup_trusted_devices
- Via scheduler (APScheduler, Celery Beat, etc.)
- Manually: python -m tasks.cleanup_trusted_devices

Recommended: Run hourly
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from loguru import logger  # noqa: E402

from repositories.database import SessionLocal  # noqa: E402
from services.trusted_device_service import TrustedDeviceService  # noqa: E402

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def cleanup_trusted_devices(
    db: "Session | None" = None,
) -> dict[str, int]:
    """
    Run cleanup for trusted devices.

    Args:
        db: Optional database session. If not provided, creates a new session.
            Useful for testing to inject a test database session.

    Returns:
        Dictionary with counts of expired and deleted devices
    """

    # Use provided session or create a new one
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        logger.info("Starting trusted device cleanup task")
        start_time = datetime.now(timezone.utc)

        # Step 1: Soft-delete expired devices
        expired_count = TrustedDeviceService.cleanup_expired_devices(db)
        if expired_count > 0:
            logger.info(f"Soft-deleted {expired_count} expired trusted devices")

        # Step 2: Permanently delete old revoked devices
        deleted_count = TrustedDeviceService.delete_old_revoked_devices(db)
        if deleted_count > 0:
            logger.info(
                f"Permanently deleted {deleted_count} revoked devices "
                f"past retention period"
            )

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"Trusted device cleanup completed in {elapsed:.2f}s - "
            f"expired: {expired_count}, deleted: {deleted_count}"
        )

        return {
            "expired_count": expired_count,
            "deleted_count": deleted_count,
        }

    except Exception as e:
        logger.error(f"Trusted device cleanup failed: {e}")
        raise
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    # Configure logging for standalone execution
    logger.remove()
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="INFO",
    )

    try:
        result = cleanup_trusted_devices()
        print(f"Cleanup completed: {result}")
        sys.exit(0)
    except Exception as e:
        print(f"Cleanup failed: {e}", file=sys.stderr)
        sys.exit(1)
