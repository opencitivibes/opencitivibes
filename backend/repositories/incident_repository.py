"""
Privacy Incident Repository for Law 25 Compliance.

Provides data access for privacy incidents (breach register).
"""

from typing import Optional

from sqlalchemy.orm import Session

from repositories import db_models
from repositories.base import BaseRepository


class IncidentRepository(BaseRepository[db_models.PrivacyIncident]):
    """Repository for privacy incident operations."""

    def __init__(self, db: Session):
        """Initialize repository."""
        super().__init__(db_models.PrivacyIncident, db)

    def _build_query(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
    ):
        """Build filtered query for incidents."""
        query = self.db.query(self.model)

        if status:
            query = query.filter(self.model.status == status)
        if severity:
            query = query.filter(self.model.severity == severity)

        return query

    def get_by_number(
        self, incident_number: str
    ) -> Optional[db_models.PrivacyIncident]:
        """Get incident by incident number."""
        return (
            self.db.query(self.model)
            .filter(self.model.incident_number == incident_number)
            .first()
        )

    def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[db_models.PrivacyIncident]:
        """
        List incidents with optional filters.

        Args:
            status: Filter by status
            severity: Filter by severity
            limit: Maximum records to return
            offset: Number of records to skip

        Returns:
            List of PrivacyIncident records
        """
        query = self._build_query(status=status, severity=severity)
        return (
            query.order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> int:
        """Count incidents with optional filters."""
        query = self._build_query(status=status, severity=severity)
        return query.count()

    def count_by_year(self, year: int) -> int:
        """Count incidents for a specific year."""
        return (
            self.db.query(self.model)
            .filter(self.model.incident_number.like(f"INC-{year}-%"))
            .count()
        )

    def get_requiring_cai_notification(self) -> list[db_models.PrivacyIncident]:
        """Get incidents requiring CAI notification."""
        return (
            self.db.query(self.model)
            .filter(
                self.model.cai_notification_required.is_(True),
                self.model.cai_notified.is_(False),
            )
            .all()
        )

    def get_requiring_user_notification(self) -> list[db_models.PrivacyIncident]:
        """Get incidents requiring user notification."""
        return (
            self.db.query(self.model)
            .filter(
                self.model.users_notification_required.is_(True),
                self.model.users_notified.is_(False),
            )
            .all()
        )
