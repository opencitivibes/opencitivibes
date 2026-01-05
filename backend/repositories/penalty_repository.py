"""
Repository for user penalty operations.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from repositories.base import BaseRepository
from repositories.db_models import (
    PenaltyStatus,
    PenaltyType,
    User,
    UserPenalty,
)


# Penalty duration in hours
PENALTY_DURATIONS: dict[PenaltyType, int | None] = {
    PenaltyType.WARNING: 0,  # No duration, just a record
    PenaltyType.TEMP_BAN_24H: 24,
    PenaltyType.TEMP_BAN_7D: 24 * 7,
    PenaltyType.TEMP_BAN_30D: 24 * 30,
    PenaltyType.PERMANENT_BAN: None,  # No expiration
}

# Lookback period for penalty progression (in days)
PENALTY_PROGRESSION_LOOKBACK: dict[PenaltyType, int] = {
    PenaltyType.WARNING: 30,
    PenaltyType.TEMP_BAN_24H: 30,
    PenaltyType.TEMP_BAN_7D: 30,
    PenaltyType.TEMP_BAN_30D: 90,
}


class PenaltyRepository(BaseRepository[UserPenalty]):
    """Repository for user penalty data access."""

    def __init__(self, db: Session):
        super().__init__(UserPenalty, db)

    def get_active_penalty(self, user_id: int) -> Optional[UserPenalty]:
        """
        Get active penalty for a user.

        Considers expired temporary bans as inactive.

        Args:
            user_id: ID of the user

        Returns:
            Active penalty if exists, None otherwise
        """
        now = datetime.now(timezone.utc)

        return (
            self.db.query(UserPenalty)
            .filter(
                UserPenalty.user_id == user_id,
                UserPenalty.status == PenaltyStatus.ACTIVE,
                or_(
                    UserPenalty.expires_at.is_(None),  # Permanent
                    UserPenalty.expires_at > now,  # Not yet expired
                ),
            )
            .order_by(UserPenalty.issued_at.desc())
            .first()
        )

    def get_user_penalties(
        self,
        user_id: int,
        include_expired: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[UserPenalty]:
        """
        Get all penalties for a user.

        Args:
            user_id: ID of the user
            include_expired: Include expired penalties
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of penalties
        """
        query = self.db.query(UserPenalty).filter(UserPenalty.user_id == user_id)

        if not include_expired:
            now = datetime.now(timezone.utc)
            query = query.filter(
                or_(
                    UserPenalty.status == PenaltyStatus.ACTIVE,
                    and_(
                        UserPenalty.expires_at.isnot(None),
                        UserPenalty.expires_at > now,
                    ),
                )
            )

        return (
            query.order_by(UserPenalty.issued_at.desc()).offset(skip).limit(limit).all()
        )

    def get_recent_penalty(
        self,
        user_id: int,
        lookback_days: int,
    ) -> Optional[UserPenalty]:
        """
        Get most recent penalty within lookback period.

        Used for penalty progression logic.

        Args:
            user_id: ID of the user
            lookback_days: Number of days to look back

        Returns:
            Most recent penalty if exists
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        return (
            self.db.query(UserPenalty)
            .filter(
                UserPenalty.user_id == user_id,
                UserPenalty.issued_at >= cutoff,
                UserPenalty.status.in_([PenaltyStatus.ACTIVE, PenaltyStatus.EXPIRED]),
            )
            .order_by(UserPenalty.issued_at.desc())
            .first()
        )

    def get_all_active_penalties(
        self,
        penalty_type: Optional[PenaltyType] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list, int]:
        """
        Get all active penalties with user info.

        Args:
            penalty_type: Filter by penalty type
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (list of (penalty, username, display_name), total_count)
        """
        now = datetime.now(timezone.utc)

        query = (
            self.db.query(UserPenalty, User.username, User.display_name)
            .join(User, UserPenalty.user_id == User.id)
            .filter(
                UserPenalty.status == PenaltyStatus.ACTIVE,
                or_(
                    UserPenalty.expires_at.is_(None),
                    UserPenalty.expires_at > now,
                ),
            )
        )

        if penalty_type:
            query = query.filter(UserPenalty.penalty_type == penalty_type)

        total = query.count()

        results = (
            query.order_by(UserPenalty.issued_at.desc()).offset(skip).limit(limit).all()
        )

        return results, total

    def expire_old_penalties(self) -> int:
        """
        Mark expired temporary bans as expired.

        Called periodically or on-demand.

        Returns:
            Number of penalties expired
        """
        now = datetime.now(timezone.utc)

        result = (
            self.db.query(UserPenalty)
            .filter(
                UserPenalty.status == PenaltyStatus.ACTIVE,
                UserPenalty.expires_at.isnot(None),
                UserPenalty.expires_at <= now,
            )
            .update(
                {UserPenalty.status: PenaltyStatus.EXPIRED},
                synchronize_session=False,
            )
        )

        self.db.commit()
        return result

    def revoke_penalty(
        self,
        penalty_id: int,
        revoked_by: int,
        reason: str,
    ) -> Optional[UserPenalty]:
        """
        Revoke an active penalty.

        Args:
            penalty_id: ID of the penalty
            revoked_by: ID of admin revoking
            reason: Reason for revocation

        Returns:
            Updated penalty if found
        """
        penalty = self.get_by_id(penalty_id)
        if not penalty:
            return None

        penalty.status = PenaltyStatus.REVOKED
        penalty.revoked_at = datetime.now(timezone.utc)
        penalty.revoked_by = revoked_by
        penalty.revoke_reason = reason

        self.db.commit()
        self.db.refresh(penalty)
        return penalty

    def count_active_penalties(self) -> int:
        """Get total count of active penalties."""
        now = datetime.now(timezone.utc)
        result = (
            self.db.query(func.count(UserPenalty.id))
            .filter(
                UserPenalty.status == PenaltyStatus.ACTIVE,
                or_(
                    UserPenalty.expires_at.is_(None),
                    UserPenalty.expires_at > now,
                ),
            )
            .scalar()
        )
        return result or 0

    def count_penalties_issued_by_admin(
        self, admin_id: int, start_date: datetime
    ) -> int:
        """
        Count penalties issued by an admin since start_date.

        Args:
            admin_id: Admin user ID
            start_date: Start date for the query

        Returns:
            Number of penalties issued
        """
        return (
            self.db.query(func.count(UserPenalty.id))
            .filter(
                UserPenalty.issued_by == admin_id,
                UserPenalty.issued_at >= start_date,
            )
            .scalar()
            or 0
        )
