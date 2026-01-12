"""
Repository for parental consent token and log operations.

Law 25 Compliance: This repository handles all database operations
for minors' parental consent workflow (users under 14).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

import repositories.db_models as db_models
from .base import BaseRepository


class ParentalConsentRepository(BaseRepository[db_models.ParentalConsentToken]):
    """Repository for parental consent token and log operations."""

    def __init__(self, db: Session):
        """
        Initialize parental consent repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.ParentalConsentToken, db)

    # =========================================================================
    # Token Operations
    # =========================================================================

    def create_token(
        self,
        pending_user_id: int,
        token_hash: str,
        parent_email: str,
        expires_at: datetime,
    ) -> db_models.ParentalConsentToken:
        """
        Create a new parental consent token.

        Args:
            pending_user_id: User ID of the minor awaiting consent
            token_hash: SHA-256 hash of the consent token
            parent_email: Parent/guardian email address
            expires_at: Token expiration datetime (UTC)

        Returns:
            Created ParentalConsentToken
        """
        token = db_models.ParentalConsentToken(
            pending_user_id=pending_user_id,
            token_hash=token_hash,
            parent_email=parent_email,
            expires_at=expires_at,
        )
        return self.create(token)

    def get_by_hash(self, token_hash: str) -> Optional[db_models.ParentalConsentToken]:
        """
        Find token by SHA-256 hash.

        Args:
            token_hash: SHA-256 hash of the token to find

        Returns:
            ParentalConsentToken if found, None otherwise
        """
        return (
            self.db.query(db_models.ParentalConsentToken)
            .filter(db_models.ParentalConsentToken.token_hash == token_hash)
            .first()
        )

    def get_active_for_user(
        self, user_id: int
    ) -> Optional[db_models.ParentalConsentToken]:
        """
        Get unexpired, unused token for a user.

        Args:
            user_id: User ID to find active token for

        Returns:
            Active ParentalConsentToken if exists, None otherwise
        """
        now = datetime.now(timezone.utc)
        return (
            self.db.query(db_models.ParentalConsentToken)
            .filter(
                db_models.ParentalConsentToken.pending_user_id == user_id,
                db_models.ParentalConsentToken.used_at.is_(None),
                db_models.ParentalConsentToken.expires_at > now,
            )
            .order_by(db_models.ParentalConsentToken.created_at.desc())
            .first()
        )

    def mark_used(
        self,
        token: db_models.ParentalConsentToken,
        decision: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> db_models.ParentalConsentToken:
        """
        Mark token as used with consent decision.

        Args:
            token: Token to mark as used
            decision: Consent decision ("granted" or "denied")
            ip_address: IP address of parent when decision was made
            user_agent: User agent of parent's browser

        Returns:
            Updated ParentalConsentToken
        """
        token.used_at = datetime.now(timezone.utc)
        token.consent_decision = decision
        token.ip_address = ip_address
        token.user_agent = user_agent
        self.commit()
        self.refresh(token)
        return token

    def get_expired(self) -> list[db_models.ParentalConsentToken]:
        """
        Find all expired tokens that haven't been used.

        Returns:
            List of expired, unused ParentalConsentTokens
        """
        now = datetime.now(timezone.utc)
        return (
            self.db.query(db_models.ParentalConsentToken)
            .filter(
                db_models.ParentalConsentToken.expires_at <= now,
                db_models.ParentalConsentToken.used_at.is_(None),
            )
            .all()
        )

    def invalidate_for_user(self, user_id: int) -> int:
        """
        Invalidate all tokens for a user by marking them as expired.

        Used when a new consent request is sent to avoid confusion
        with multiple active tokens.

        Args:
            user_id: User ID to invalidate tokens for

        Returns:
            Number of tokens invalidated
        """
        now = datetime.now(timezone.utc)
        count = (
            self.db.query(db_models.ParentalConsentToken)
            .filter(
                db_models.ParentalConsentToken.pending_user_id == user_id,
                db_models.ParentalConsentToken.used_at.is_(None),
                db_models.ParentalConsentToken.expires_at > now,
            )
            .update(
                {db_models.ParentalConsentToken.expires_at: now},
                synchronize_session=False,
            )
        )
        return count

    def cleanup_old_tokens(self, days: int = 30) -> int:
        """
        Delete old expired tokens for cleanup.

        Args:
            days: Delete tokens expired more than this many days ago

        Returns:
            Number of tokens deleted
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        count = (
            self.db.query(db_models.ParentalConsentToken)
            .filter(
                db_models.ParentalConsentToken.expires_at < cutoff,
            )
            .delete(synchronize_session=False)
        )
        self.commit()
        return count

    # =========================================================================
    # Log Operations
    # =========================================================================

    def create_log(
        self,
        user_id: int,
        action: str,
        parent_email: str,
        token_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> db_models.ParentalConsentLog:
        """
        Create a consent log entry.

        Log entries are immutable - once created, they should not be
        modified or deleted (for audit compliance).

        Args:
            user_id: User ID this log relates to
            action: Action type (request_sent, consent_granted,
                    consent_denied, consent_expired)
            parent_email: Parent/guardian email at time of action
            token_id: Related consent token ID (if applicable)
            ip_address: IP address when action occurred
            user_agent: User agent when action occurred
            notes: Additional notes about the action

        Returns:
            Created ParentalConsentLog
        """
        log = db_models.ParentalConsentLog(
            user_id=user_id,
            action=action,
            parent_email=parent_email,
            token_id=token_id,
            ip_address=ip_address,
            user_agent=user_agent,
            notes=notes,
        )
        self.db.add(log)
        self.commit()
        self.db.refresh(log)
        return log

    def get_logs_for_user(self, user_id: int) -> list[db_models.ParentalConsentLog]:
        """
        Get all consent logs for a user.

        Args:
            user_id: User ID to get logs for

        Returns:
            List of ParentalConsentLogs ordered by most recent first
        """
        return (
            self.db.query(db_models.ParentalConsentLog)
            .filter(db_models.ParentalConsentLog.user_id == user_id)
            .order_by(db_models.ParentalConsentLog.created_at.desc())
            .all()
        )

    def get_logs_by_action(
        self, action: str, limit: int = 100
    ) -> list[db_models.ParentalConsentLog]:
        """
        Get logs filtered by action type.

        Args:
            action: Action type to filter by
            limit: Maximum number of logs to return

        Returns:
            List of ParentalConsentLogs matching the action
        """
        return (
            self.db.query(db_models.ParentalConsentLog)
            .filter(db_models.ParentalConsentLog.action == action)
            .order_by(db_models.ParentalConsentLog.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_recent_logs(self, days: int = 30) -> list[db_models.ParentalConsentLog]:
        """
        Get logs from the last N days for auditing.

        Args:
            days: Number of days to look back

        Returns:
            List of ParentalConsentLogs from the specified period
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            self.db.query(db_models.ParentalConsentLog)
            .filter(db_models.ParentalConsentLog.created_at >= cutoff)
            .order_by(db_models.ParentalConsentLog.created_at.desc())
            .all()
        )

    # =========================================================================
    # Cleanup Operations
    # =========================================================================

    def get_accounts_pending_deletion(
        self, grace_period_days: int = 30
    ) -> list[db_models.User]:
        """
        Get accounts with denied consent past the grace period.

        These accounts should be deleted per Law 25 requirements.

        Args:
            grace_period_days: Days after denial before deletion

        Returns:
            List of Users with denied consent past grace period
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=grace_period_days)
        return (
            self.db.query(db_models.User)
            .filter(
                db_models.User.parental_consent_status == "denied",
                db_models.User.is_active.is_(False),
            )
            .join(
                db_models.ParentalConsentToken,
                db_models.ParentalConsentToken.pending_user_id == db_models.User.id,
            )
            .filter(
                db_models.ParentalConsentToken.consent_decision == "denied",
                db_models.ParentalConsentToken.used_at < cutoff,
            )
            .distinct()
            .all()
        )
