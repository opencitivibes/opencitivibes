"""
Security Audit Log Repository for Law 25 Compliance.

Provides data access for security audit logs and suspicious pattern detection.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from repositories import db_models
from repositories.base import BaseRepository


class SecurityAuditRepository(BaseRepository[db_models.SecurityAuditLog]):
    """Repository for security audit log operations."""

    def __init__(self, db: Session):
        """Initialize repository."""
        super().__init__(db_models.SecurityAuditLog, db)

    def _build_query(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """Build filtered query for audit logs."""
        query = self.db.query(self.model)

        if event_type:
            query = query.filter(self.model.event_type == event_type)
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        if ip_address:
            query = query.filter(self.model.ip_address == ip_address)
        if severity:
            query = query.filter(self.model.severity == severity)
        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)

        return query

    def get_logs(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[db_models.SecurityAuditLog]:
        """
        Get audit logs with filters.

        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            ip_address: Filter by IP address
            severity: Filter by severity level
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum records to return
            offset: Number of records to skip

        Returns:
            List of matching SecurityAuditLog entries
        """
        query = self._build_query(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            severity=severity,
            start_date=start_date,
            end_date=end_date,
        )
        return (
            query.order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_logs(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[int] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Count audit logs matching filters."""
        query = self._build_query(
            event_type=event_type,
            user_id=user_id,
            severity=severity,
            start_date=start_date,
            end_date=end_date,
        )
        result = query.count()
        return result or 0

    def get_failed_logins_by_ip(
        self,
        event_type: str,
        since: datetime,
        threshold: int,
    ) -> list[tuple[str, int]]:
        """
        Get IPs with failed logins exceeding threshold.

        Args:
            event_type: Event type to filter
            since: Start time for search
            threshold: Minimum count to include

        Returns:
            List of (ip_address, count) tuples
        """
        rows = (
            self.db.query(
                self.model.ip_address,
                func.count(self.model.id).label("count"),
            )
            .filter(
                self.model.event_type == event_type,
                self.model.created_at >= since,
                self.model.ip_address.isnot(None),
            )
            .group_by(self.model.ip_address)
            .having(func.count(self.model.id) > threshold)
            .all()
        )
        return [(str(row[0]), int(row[1])) for row in rows]

    def get_exports_by_user(
        self,
        event_type: str,
        since: datetime,
        threshold: int,
    ) -> list[tuple[int, int]]:
        """
        Get users with exports exceeding threshold.

        Args:
            event_type: Event type to filter
            since: Start time for search
            threshold: Minimum count to include

        Returns:
            List of (user_id, count) tuples
        """
        rows = (
            self.db.query(
                self.model.user_id,
                func.count(self.model.id).label("count"),
            )
            .filter(
                self.model.event_type == event_type,
                self.model.created_at >= since,
                self.model.user_id.isnot(None),
            )
            .group_by(self.model.user_id)
            .having(func.count(self.model.id) > threshold)
            .all()
        )
        return [(int(row[0]), int(row[1])) for row in rows]

    def get_admin_access_by_user(
        self,
        event_type: str,
        since: datetime,
        threshold: int,
    ) -> list[tuple[int, int]]:
        """
        Get admins with PII access exceeding threshold.

        Args:
            event_type: Event type to filter
            since: Start time for search
            threshold: Minimum count to include

        Returns:
            List of (user_id, count) tuples
        """
        rows = (
            self.db.query(
                self.model.user_id,
                func.count(self.model.id).label("count"),
            )
            .filter(
                self.model.event_type == event_type,
                self.model.created_at >= since,
            )
            .group_by(self.model.user_id)
            .having(func.count(self.model.id) > threshold)
            .all()
        )
        return [(int(row[0]), int(row[1])) for row in rows]
