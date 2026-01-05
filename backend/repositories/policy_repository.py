"""
Policy Repository for Law 25 Compliance.

Handles database operations for policy versions and consent logging.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from repositories import db_models
from repositories.base import BaseRepository


class PolicyRepository(BaseRepository[db_models.PolicyVersion]):
    """Repository for policy version and consent data access."""

    def __init__(self, db: Session):
        """Initialize repository."""
        super().__init__(db_models.PolicyVersion, db)

    def get_policy_versions(
        self,
        policy_type: str,
        since_date: Optional[datetime] = None,
    ) -> list[db_models.PolicyVersion]:
        """
        Get policy versions for a type, optionally filtered by date.

        Args:
            policy_type: 'privacy' or 'terms'
            since_date: Only return versions after this date

        Returns:
            List of policy versions ordered by effective_date desc
        """
        query = self.db.query(db_models.PolicyVersion).filter(
            db_models.PolicyVersion.policy_type == policy_type
        )

        if since_date:
            query = query.filter(db_models.PolicyVersion.effective_date > since_date)

        return query.order_by(db_models.PolicyVersion.effective_date.desc()).all()

    def get_policy_version(
        self,
        policy_type: str,
        version: str,
    ) -> Optional[db_models.PolicyVersion]:
        """
        Get a specific policy version.

        Args:
            policy_type: 'privacy' or 'terms'
            version: Version string (e.g., '1.0')

        Returns:
            PolicyVersion if found, None otherwise
        """
        return (
            self.db.query(db_models.PolicyVersion)
            .filter(
                db_models.PolicyVersion.policy_type == policy_type,
                db_models.PolicyVersion.version == version,
            )
            .first()
        )

    def add_consent_log(
        self,
        user_id: int,
        consent_type: str,
        action: str,
        policy_version: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> db_models.ConsentLog:
        """
        Add a consent log entry.

        Args:
            user_id: User ID
            consent_type: Type of consent (e.g., 'privacy', 'terms')
            action: Action taken (e.g., 'reconsented')
            policy_version: Version of the policy
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created ConsentLog entry
        """
        log = db_models.ConsentLog(
            user_id=user_id,
            consent_type=consent_type,
            action=action,
            policy_version=policy_version,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        self.db.commit()
        return log
