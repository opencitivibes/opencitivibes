"""
Login event repository for database operations.

Provides data access methods for login event tracking and security auditing.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

import repositories.db_models as db_models
from .base import BaseRepository


class LoginEventRepository(BaseRepository[db_models.LoginEvent]):
    """Repository for LoginEvent entity database operations."""

    def __init__(self, db: Session):
        """
        Initialize login event repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.LoginEvent, db)

    def create_event(
        self,
        event_type: db_models.LoginEventType,
        email: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        failure_reason: Optional[db_models.LoginFailureReason] = None,
        metadata_json: Optional[str] = None,
    ) -> db_models.LoginEvent:
        """
        Create a new login event.

        Args:
            event_type: Type of login event
            email: Email used in login attempt
            user_id: User ID (if known)
            ip_address: Client IP address
            user_agent: Browser user agent string
            failure_reason: Reason for failure (if applicable)
            metadata_json: Additional JSON metadata

        Returns:
            Created login event
        """
        event = db_models.LoginEvent(
            event_type=event_type,
            email=email,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason=failure_reason,
            metadata_json=metadata_json,
        )
        return self.create(event)

    def get_recent_events(
        self,
        skip: int = 0,
        limit: int = 100,
        event_type: Optional[db_models.LoginEventType] = None,
    ) -> list[db_models.LoginEvent]:
        """
        Get recent login events with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            event_type: Optional filter by event type

        Returns:
            List of login events ordered by created_at descending
        """
        query = self.db.query(db_models.LoginEvent)

        if event_type is not None:
            query = query.filter(db_models.LoginEvent.event_type == event_type)

        return (
            query.order_by(db_models.LoginEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_failed_attempts_count(
        self,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        window_minutes: int = 15,
    ) -> int:
        """
        Count failed login attempts within a time window.

        Used for rate limiting and security monitoring.

        Args:
            email: Filter by email address
            ip_address: Filter by IP address
            window_minutes: Time window in minutes (default 15)

        Returns:
            Count of failed attempts
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        query = self.db.query(func.count(db_models.LoginEvent.id)).filter(
            db_models.LoginEvent.event_type == db_models.LoginEventType.LOGIN_FAILED,
            db_models.LoginEvent.created_at >= cutoff,
        )

        if email is not None:
            query = query.filter(db_models.LoginEvent.email == email)

        if ip_address is not None:
            query = query.filter(db_models.LoginEvent.ip_address == ip_address)

        result = query.scalar()
        return result if result is not None else 0

    def get_events_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        event_type: Optional[db_models.LoginEventType] = None,
    ) -> list[db_models.LoginEvent]:
        """
        Get login events for a specific user.

        Args:
            user_id: User ID to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            event_type: Optional filter by event type

        Returns:
            List of login events for the user
        """
        query = self.db.query(db_models.LoginEvent).filter(
            db_models.LoginEvent.user_id == user_id
        )

        if event_type is not None:
            query = query.filter(db_models.LoginEvent.event_type == event_type)

        return (
            query.order_by(db_models.LoginEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_events_by_ip(
        self,
        ip_address: str,
        skip: int = 0,
        limit: int = 100,
        hours: int = 24,
    ) -> list[db_models.LoginEvent]:
        """
        Get login events from a specific IP address.

        Args:
            ip_address: IP address to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            hours: Time window in hours (default 24)

        Returns:
            List of login events from the IP
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        return (
            self.db.query(db_models.LoginEvent)
            .filter(
                db_models.LoginEvent.ip_address == ip_address,
                db_models.LoginEvent.created_at >= cutoff,
            )
            .order_by(db_models.LoginEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def cleanup_old_events(self, retention_days: int = 90) -> int:
        """
        Delete login events older than the retention period.

        Args:
            retention_days: Number of days to retain events (default 90)

        Returns:
            Number of deleted events
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        deleted_count = (
            self.db.query(db_models.LoginEvent)
            .filter(db_models.LoginEvent.created_at < cutoff)
            .delete(synchronize_session=False)
        )

        self.commit()
        return deleted_count

    def count_events_in_window(
        self,
        window_hours: int = 24,
        event_type: Optional[db_models.LoginEventType] = None,
    ) -> int:
        """
        Count events within a time window.

        Args:
            window_hours: Time window in hours (default 24)
            event_type: Optional filter by event type

        Returns:
            Count of events
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        query = self.db.query(func.count(db_models.LoginEvent.id)).filter(
            db_models.LoginEvent.created_at >= cutoff
        )

        if event_type is not None:
            query = query.filter(db_models.LoginEvent.event_type == event_type)

        result = query.scalar()
        return result if result is not None else 0

    def get_unique_ips_count(self, window_hours: int = 24) -> int:
        """
        Count unique IP addresses in a time window.

        Args:
            window_hours: Time window in hours (default 24)

        Returns:
            Count of unique IPs
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        result = (
            self.db.query(func.count(func.distinct(db_models.LoginEvent.ip_address)))
            .filter(
                db_models.LoginEvent.created_at >= cutoff,
                db_models.LoginEvent.ip_address.isnot(None),
            )
            .scalar()
        )
        return result if result is not None else 0

    def get_failure_reason_counts(
        self, window_hours: int = 24
    ) -> list[tuple[Optional[db_models.LoginFailureReason], int]]:
        """
        Get counts of failure reasons in a time window.

        Args:
            window_hours: Time window in hours (default 24)

        Returns:
            List of (reason, count) tuples
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        results = (
            self.db.query(
                db_models.LoginEvent.failure_reason,
                func.count(db_models.LoginEvent.id),
            )
            .filter(
                db_models.LoginEvent.event_type
                == db_models.LoginEventType.LOGIN_FAILED,
                db_models.LoginEvent.created_at >= cutoff,
                db_models.LoginEvent.failure_reason.isnot(None),
            )
            .group_by(db_models.LoginEvent.failure_reason)
            .order_by(func.count(db_models.LoginEvent.id).desc())
            .all()
        )
        return [(row[0], int(row[1])) for row in results]

    def get_suspicious_ips(
        self,
        window_hours: int = 24,
        failure_threshold: int = 5,
        limit: int = 10,
    ) -> list[tuple[str, int, int]]:
        """
        Get IPs with high failure rates.

        Args:
            window_hours: Time window in hours (default 24)
            failure_threshold: Minimum failures to be considered suspicious
            limit: Maximum number of IPs to return

        Returns:
            List of (ip_address, failure_count, total_count) tuples
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # Subquery for failure counts - use imported case function
        from sqlalchemy import case

        failure_count = func.sum(
            case(
                (
                    db_models.LoginEvent.event_type
                    == db_models.LoginEventType.LOGIN_FAILED,
                    1,
                ),
                else_=0,
            )
        ).label("failure_count")

        total_count = func.count(db_models.LoginEvent.id).label("total_count")

        results = (
            self.db.query(
                db_models.LoginEvent.ip_address,
                failure_count,
                total_count,
            )
            .filter(
                db_models.LoginEvent.created_at >= cutoff,
                db_models.LoginEvent.ip_address.isnot(None),
            )
            .group_by(db_models.LoginEvent.ip_address)
            .having(failure_count >= failure_threshold)
            .order_by(failure_count.desc())
            .limit(limit)
            .all()
        )

        return [(r[0], int(r[1]), int(r[2])) for r in results]

    def get_events_with_filters(
        self,
        skip: int = 0,
        limit: int = 50,
        event_type: Optional[db_models.LoginEventType] = None,
        user_id: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> list[db_models.LoginEvent]:
        """
        Get events with comprehensive filtering options.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            event_type: Optional filter by event type
            user_id: Optional filter by user ID
            since: Optional filter for events after this datetime

        Returns:
            List of login events matching filters
        """
        query = self.db.query(db_models.LoginEvent)

        if event_type is not None:
            query = query.filter(db_models.LoginEvent.event_type == event_type)

        if user_id is not None:
            query = query.filter(db_models.LoginEvent.user_id == user_id)

        if since is not None:
            query = query.filter(db_models.LoginEvent.created_at >= since)

        return (
            query.order_by(db_models.LoginEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_events_with_filters(
        self,
        event_type: Optional[db_models.LoginEventType] = None,
        user_id: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """
        Count events matching filters.

        Args:
            event_type: Optional filter by event type
            user_id: Optional filter by user ID
            since: Optional filter for events after this datetime

        Returns:
            Count of matching events
        """
        query = self.db.query(func.count(db_models.LoginEvent.id))

        if event_type is not None:
            query = query.filter(db_models.LoginEvent.event_type == event_type)

        if user_id is not None:
            query = query.filter(db_models.LoginEvent.user_id == user_id)

        if since is not None:
            query = query.filter(db_models.LoginEvent.created_at >= since)

        result = query.scalar()
        return result if result is not None else 0

    def get_admin_logins(
        self,
        window_hours: int = 24,
        limit: int = 10,
    ) -> list[db_models.LoginEvent]:
        """
        Get recent admin login events.

        Joins with User table to find admin logins.

        Args:
            window_hours: Time window in hours (default 24)
            limit: Maximum number of records to return

        Returns:
            List of admin login events
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # Join with User to filter admin logins
        return (
            self.db.query(db_models.LoginEvent)
            .join(db_models.User, db_models.LoginEvent.user_id == db_models.User.id)
            .filter(
                db_models.LoginEvent.event_type
                == db_models.LoginEventType.LOGIN_SUCCESS,
                db_models.LoginEvent.created_at >= cutoff,
                db_models.User.is_global_admin == True,  # noqa: E712
            )
            .order_by(db_models.LoginEvent.created_at.desc())
            .limit(limit)
            .all()
        )

    def count_admin_logins(self, window_hours: int = 24) -> int:
        """
        Count admin logins in a time window.

        Args:
            window_hours: Time window in hours (default 24)

        Returns:
            Count of admin logins
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        result = (
            self.db.query(func.count(db_models.LoginEvent.id))
            .join(db_models.User, db_models.LoginEvent.user_id == db_models.User.id)
            .filter(
                db_models.LoginEvent.event_type
                == db_models.LoginEventType.LOGIN_SUCCESS,
                db_models.LoginEvent.created_at >= cutoff,
                db_models.User.is_global_admin == True,  # noqa: E712
            )
            .scalar()
        )
        return result if result is not None else 0

    def get_failed_attempts_by_ip_in_window(
        self,
        window_hours: int = 1,
        min_failures: int = 3,
        limit: int = 10,
    ) -> list[tuple[str, int, Optional[datetime]]]:
        """
        Get IPs with multiple failures in the last hour for brute force detection.

        Args:
            window_hours: Time window in hours (default 1)
            min_failures: Minimum failures to include (default 3)
            limit: Maximum IPs to return

        Returns:
            List of (ip_address, failure_count, last_attempt_time) tuples
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        results = (
            self.db.query(
                db_models.LoginEvent.ip_address,
                func.count(db_models.LoginEvent.id).label("count"),
                func.max(db_models.LoginEvent.created_at).label("last_attempt"),
            )
            .filter(
                db_models.LoginEvent.event_type
                == db_models.LoginEventType.LOGIN_FAILED,
                db_models.LoginEvent.created_at >= cutoff,
                db_models.LoginEvent.ip_address.isnot(None),
            )
            .group_by(db_models.LoginEvent.ip_address)
            .having(func.count(db_models.LoginEvent.id) >= min_failures)
            .order_by(func.count(db_models.LoginEvent.id).desc())
            .limit(limit)
            .all()
        )

        return [(r[0], int(r[1]), r[2]) for r in results]
