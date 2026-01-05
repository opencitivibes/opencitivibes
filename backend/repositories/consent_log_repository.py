"""
Consent Log Repository for Law 25 Compliance.

Provides CRUD operations for consent audit logging.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

import repositories.db_models as db_models

from .base import BaseRepository


class ConsentLogRepository(BaseRepository[db_models.ConsentLog]):
    """Repository for consent log operations."""

    def __init__(self, db: Session):
        """
        Initialize consent log repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.ConsentLog, db)

    def create_consent_log(
        self,
        user_id: int,
        consent_type: str,
        action: str,
        policy_version: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> db_models.ConsentLog:
        """
        Create a new consent log entry.

        Args:
            user_id: User ID
            consent_type: Type of consent (account, terms, privacy, marketing)
            action: Action taken (granted, withdrawn, deleted, etc.)
            policy_version: Optional policy version reference
            ip_address: Optional IP address for audit

        Returns:
            Created ConsentLog record
        """
        log = db_models.ConsentLog(
            user_id=user_id,
            consent_type=consent_type,
            action=action,
            policy_version=policy_version,
            ip_address=ip_address,
        )
        return self.create(log)

    def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[db_models.ConsentLog]:
        """
        Get consent logs for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of consent logs
        """
        return (
            self.db.query(db_models.ConsentLog)
            .filter(db_models.ConsentLog.user_id == user_id)
            .order_by(db_models.ConsentLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def delete_old_logs_for_deleted_users(
        self,
        cutoff_date: datetime,
    ) -> int:
        """
        Delete consent logs older than cutoff for deleted/anonymized users.

        Args:
            cutoff_date: Delete logs older than this date

        Returns:
            Number of deleted logs
        """
        deleted_count = (
            self.db.query(db_models.ConsentLog)
            .filter(
                db_models.ConsentLog.created_at < cutoff_date,
                db_models.ConsentLog.user_id.in_(
                    self.db.query(db_models.User.id).filter(
                        db_models.User.is_active == False,  # noqa: E712
                        db_models.User.email.like("deleted-user-%"),
                    )
                ),
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted_count
