"""
Service for user penalty business logic.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.exceptions import (
    CannotRevokePenaltyException,
    PenaltyNotFoundException,
    UserAlreadyPenalizedException,
    UserNotFoundException,
)
from repositories.db_models import (
    PenaltyStatus,
    PenaltyType,
    UserPenalty,
)
from repositories.penalty_repository import (
    PENALTY_DURATIONS,
    PENALTY_PROGRESSION_LOOKBACK,
    PenaltyRepository,
)
from services.trust_score_service import TrustScoreService


# Penalty progression order
PENALTY_ORDER = [
    PenaltyType.WARNING,
    PenaltyType.TEMP_BAN_24H,
    PenaltyType.TEMP_BAN_7D,
    PenaltyType.TEMP_BAN_30D,
    PenaltyType.PERMANENT_BAN,
]


class PenaltyService:
    """Service for user penalty operations."""

    @staticmethod
    def issue_penalty(
        db: Session,
        user_id: int,
        penalty_type: PenaltyType,
        reason: str,
        issued_by: int,
        related_flag_ids: Optional[list[int]] = None,
        bulk_delete_content: bool = False,
    ) -> UserPenalty:
        """
        Issue a penalty to a user.

        Args:
            db: Database session
            user_id: ID of user to penalize
            penalty_type: Type of penalty
            reason: Reason for penalty
            issued_by: ID of admin issuing penalty
            related_flag_ids: IDs of related flags
            bulk_delete_content: Delete user's pending content

        Returns:
            Created penalty

        Raises:
            UserNotFoundException: If user not found
            UserAlreadyPenalizedException: If user has equal/higher penalty
        """
        from repositories.user_repository import UserRepository

        penalty_repo = PenaltyRepository(db)
        user_repo = UserRepository(db)

        # Verify user exists
        user = user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found")

        # Check for existing active penalty
        active_penalty = penalty_repo.get_active_penalty(user_id)
        if active_penalty:
            active_level = PENALTY_ORDER.index(active_penalty.penalty_type)
            new_level = PENALTY_ORDER.index(penalty_type)
            if new_level <= active_level:
                raise UserAlreadyPenalizedException(
                    f"User already has an active {active_penalty.penalty_type.value} penalty"
                )

        # Calculate expiration
        duration_hours = PENALTY_DURATIONS.get(penalty_type)
        expires_at = None
        if duration_hours:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=duration_hours)

        # Create penalty
        penalty = UserPenalty(
            user_id=user_id,
            penalty_type=penalty_type,
            reason=reason,
            status=PenaltyStatus.ACTIVE,
            issued_by=issued_by,
            expires_at=expires_at,
            related_flag_ids=json.dumps(related_flag_ids) if related_flag_ids else None,
        )
        penalty_repo.add(penalty)

        # Bulk delete pending content if requested
        if bulk_delete_content and penalty_type != PenaltyType.WARNING:
            PenaltyService._bulk_delete_user_content(db, user_id, issued_by, reason)

        penalty_repo.commit()
        penalty_repo.refresh(penalty)

        # Update user's trust score
        TrustScoreService.update_user_trust_score(db, user_id)

        return penalty

    @staticmethod
    def get_next_penalty_type(db: Session, user_id: int) -> PenaltyType:
        """
        Determine next penalty type based on user's history.

        Uses lookback periods to determine progression.

        Args:
            db: Database session
            user_id: ID of user

        Returns:
            Next penalty type in progression
        """
        penalty_repo = PenaltyRepository(db)

        # Start from most severe and work down (skip permanent)
        for penalty_type in reversed(PENALTY_ORDER[:-1]):
            lookback = PENALTY_PROGRESSION_LOOKBACK.get(penalty_type, 30)
            recent = penalty_repo.get_recent_penalty(user_id, lookback)

            if recent:
                # Find this penalty in the order
                current_idx = PENALTY_ORDER.index(recent.penalty_type)
                next_idx = min(current_idx + 1, len(PENALTY_ORDER) - 1)
                return PENALTY_ORDER[next_idx]

        # No recent penalty, start with warning
        return PenaltyType.WARNING

    @staticmethod
    def check_user_banned(db: Session, user_id: int) -> Optional[UserPenalty]:
        """
        Check if user is currently banned.

        Args:
            db: Database session
            user_id: ID of user

        Returns:
            Active ban penalty if exists, None otherwise
        """
        penalty_repo = PenaltyRepository(db)
        active = penalty_repo.get_active_penalty(user_id)

        if active and active.penalty_type != PenaltyType.WARNING:
            return active

        return None

    @staticmethod
    def revoke_penalty(
        db: Session,
        penalty_id: int,
        revoked_by: int,
        reason: str,
    ) -> UserPenalty:
        """
        Revoke an active penalty.

        Args:
            db: Database session
            penalty_id: ID of penalty to revoke
            revoked_by: ID of admin revoking
            reason: Reason for revocation

        Returns:
            Updated penalty

        Raises:
            PenaltyNotFoundException: If penalty not found
            CannotRevokePenaltyException: If penalty cannot be revoked
        """
        penalty_repo = PenaltyRepository(db)

        penalty = penalty_repo.get_by_id(penalty_id)
        if not penalty:
            raise PenaltyNotFoundException(penalty_id)

        if penalty.status != PenaltyStatus.ACTIVE:
            raise CannotRevokePenaltyException(
                f"Penalty is {penalty.status.value}, cannot revoke"
            )

        revoked = penalty_repo.revoke_penalty(penalty_id, revoked_by, reason)
        if not revoked:
            raise PenaltyNotFoundException(penalty_id)

        # Update user's trust score
        TrustScoreService.update_user_trust_score(db, int(penalty.user_id))

        return revoked

    @staticmethod
    def get_user_penalties(
        db: Session,
        user_id: int,
        include_expired: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[UserPenalty]:
        """
        Get all penalties for a user.

        Args:
            db: Database session
            user_id: ID of user
            include_expired: Include expired penalties
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of penalties
        """
        penalty_repo = PenaltyRepository(db)
        return penalty_repo.get_user_penalties(user_id, include_expired, skip, limit)

    @staticmethod
    def expire_penalties(db: Session) -> int:
        """
        Expire old temporary bans.

        Should be called periodically.

        Returns:
            Number of penalties expired
        """
        penalty_repo = PenaltyRepository(db)
        return penalty_repo.expire_old_penalties()

    @staticmethod
    def _bulk_delete_user_content(
        db: Session,
        user_id: int,
        deleted_by: int,
        reason: str,
    ) -> None:
        """
        Soft delete all pending content from a user.

        Used when banning a user.
        """
        from repositories.comment_repository import CommentRepository
        from repositories.idea_repository import IdeaRepository

        comment_repo = CommentRepository(db)
        idea_repo = IdeaRepository(db)

        # Delete pending comments
        comment_repo.bulk_soft_delete_by_user(
            user_id, deleted_by, f"User banned: {reason}"
        )

        # Delete pending ideas
        idea_repo.bulk_soft_delete_by_user(
            user_id, deleted_by, f"User banned: {reason}"
        )

    @staticmethod
    def get_all_active_penalties(
        db: Session,
        penalty_type: Optional[PenaltyType] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """
        Get all active penalties with user information.

        Args:
            db: Database session
            penalty_type: Filter by penalty type (optional)
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (list of penalty dicts with user info, total count)
        """
        penalty_repo = PenaltyRepository(db)
        penalties, total = penalty_repo.get_all_active_penalties(
            penalty_type, skip, limit
        )

        return (
            [
                {
                    "id": p.id,
                    "user_id": p.user_id,
                    "user_username": username,
                    "user_display_name": display_name,
                    "penalty_type": p.penalty_type,
                    "reason": p.reason,
                    "status": p.status,
                    "issued_at": p.issued_at,
                    "expires_at": p.expires_at,
                }
                for p, username, display_name in penalties
            ],
            total,
        )

    @staticmethod
    def can_appeal(penalty: UserPenalty) -> bool:
        """
        Check if a penalty can be appealed.

        Args:
            penalty: Penalty to check

        Returns:
            True if can be appealed
        """
        # Must be active
        if penalty.status != PenaltyStatus.ACTIVE:
            return False

        # Check if already has appeal
        if hasattr(penalty, "appeal") and penalty.appeal:
            return False

        # Warnings cannot be appealed
        if penalty.penalty_type == PenaltyType.WARNING:
            return False

        return True
