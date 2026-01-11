#!/usr/bin/env python
"""
Script to clean up expired password reset tokens.

Can be run via:
- Cron: 0 * * * * cd /path/to/backend && python scripts/cleanup_tokens.py
- Manual: python scripts/cleanup_tokens.py
- Systemd timer: See /etc/systemd/system/cleanup-tokens.service

Options:
    --older-than-hours N: Delete tokens expired more than N hours ago (default: 24)
    --dry-run: Show what would be deleted without actually deleting
"""

import argparse
import sys
from pathlib import Path

# Add the backend directory to the path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from sqlalchemy.orm import Session

from repositories.database import SessionLocal
from services.password_reset_service import PasswordResetService


def main() -> int:
    """Run the token cleanup."""
    parser = argparse.ArgumentParser(
        description="Clean up expired password reset tokens"
    )
    parser.add_argument(
        "--older-than-hours",
        type=int,
        default=24,
        help="Delete tokens expired more than N hours ago (default: 24)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    db: Session = SessionLocal()
    try:
        if args.dry_run:
            # For dry run, just count what would be deleted
            from datetime import datetime, timedelta, timezone

            from repositories.db_models import PasswordResetToken

            cutoff = datetime.now(timezone.utc) - timedelta(hours=args.older_than_hours)
            count = (
                db.query(PasswordResetToken)
                .filter(PasswordResetToken.expires_at < cutoff)
                .count()
            )
            logger.info(
                f"[DRY RUN] Would delete {count} expired tokens older than {args.older_than_hours} hours"
            )
        else:
            count = PasswordResetService.cleanup_expired_tokens(
                db, older_than_hours=args.older_than_hours
            )
            logger.info(
                f"Deleted {count} expired tokens older than {args.older_than_hours} hours"
            )
        return 0
    except Exception as e:
        logger.error(f"Token cleanup failed: {e}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
