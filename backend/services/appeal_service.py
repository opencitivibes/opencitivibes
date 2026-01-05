"""
Service for appeal business logic.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.exceptions import (
    AppealAlreadyExistsException,
    AppealNotFoundException,
    CannotAppealException,
    PenaltyNotFoundException,
)
from repositories.appeal_repository import AppealRepository
from repositories.db_models import Appeal, AppealStatus, PenaltyStatus
from repositories.penalty_repository import PenaltyRepository
from services.penalty_service import PenaltyService
from services.trust_score_service import TrustScoreService


class AppealService:
    """Service for appeal operations."""

    @staticmethod
    def submit_appeal(
        db: Session,
        penalty_id: int,
        user_id: int,
        reason: str,
    ) -> Appeal:
        """
        Submit an appeal for a penalty.

        Args:
            db: Database session
            penalty_id: ID of penalty to appeal
            user_id: ID of user submitting appeal
            reason: Appeal reason

        Returns:
            Created appeal

        Raises:
            PenaltyNotFoundException: If penalty not found
            CannotAppealException: If penalty cannot be appealed
            AppealAlreadyExistsException: If appeal already exists
        """
        penalty_repo = PenaltyRepository(db)
        appeal_repo = AppealRepository(db)

        # Get penalty
        penalty = penalty_repo.get_by_id(penalty_id)
        if not penalty:
            raise PenaltyNotFoundException(penalty_id)

        # Verify user owns the penalty
        if int(penalty.user_id) != user_id:
            raise PenaltyNotFoundException(penalty_id)

        # Check for existing appeal first (more specific error message)
        existing = appeal_repo.get_by_penalty(penalty_id)
        if existing:
            raise AppealAlreadyExistsException()

        # Check if can be appealed
        if not PenaltyService.can_appeal(penalty):
            raise CannotAppealException(
                "This penalty cannot be appealed. "
                "Warnings and already-appealed penalties are not eligible."
            )

        # Create appeal
        appeal = Appeal(
            penalty_id=penalty_id,
            user_id=user_id,
            reason=reason,
            status=AppealStatus.PENDING,
        )
        appeal_repo.add(appeal)

        # Mark penalty as appealed
        penalty.status = PenaltyStatus.APPEALED

        appeal_repo.commit()
        appeal_repo.refresh(appeal)
        return appeal

    @staticmethod
    def review_appeal(
        db: Session,
        appeal_id: int,
        reviewer_id: int,
        action: str,
        review_notes: str,
    ) -> Appeal:
        """
        Review an appeal.

        Args:
            db: Database session
            appeal_id: ID of appeal
            reviewer_id: ID of reviewing admin
            action: "approve" or "reject"
            review_notes: Review notes

        Returns:
            Updated appeal

        Raises:
            AppealNotFoundException: If appeal not found
        """
        appeal_repo = AppealRepository(db)
        penalty_repo = PenaltyRepository(db)

        appeal = appeal_repo.get_by_id(appeal_id)
        if not appeal:
            raise AppealNotFoundException(appeal_id)

        if appeal.status != AppealStatus.PENDING:
            raise AppealNotFoundException(appeal_id)  # Already reviewed

        now = datetime.now(timezone.utc)

        if action == "approve":
            # Approve appeal - revoke penalty
            new_status = AppealStatus.APPROVED
            penalty = penalty_repo.get_by_id(int(appeal.penalty_id))
            if penalty:
                penalty.status = PenaltyStatus.REVOKED
                penalty.revoked_at = now
                penalty.revoked_by = reviewer_id
                penalty.revoke_reason = f"Appeal approved: {review_notes}"

            # Update user's trust score
            TrustScoreService.update_user_trust_score(db, int(appeal.user_id))
        else:
            # Reject appeal - reactivate penalty
            new_status = AppealStatus.REJECTED
            penalty = penalty_repo.get_by_id(int(appeal.penalty_id))
            if penalty:
                penalty.status = PenaltyStatus.ACTIVE

        updated = appeal_repo.update_appeal_status(
            appeal_id, new_status, reviewer_id, review_notes
        )
        if not updated:
            raise AppealNotFoundException(appeal_id)

        return updated

    @staticmethod
    def get_user_appeals(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Appeal]:
        """Get all appeals for a user."""
        appeal_repo = AppealRepository(db)
        return appeal_repo.get_user_appeals(user_id, skip, limit)

    @staticmethod
    def get_pending_appeals(
        db: Session,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """
        Get pending appeals for admin review.

        Returns:
            Tuple of (list of appeal dicts with user info, total)
        """
        appeal_repo = AppealRepository(db)
        appeals_with_users, total = appeal_repo.get_pending_appeals(skip, limit)

        return [
            {
                "id": appeal.id,
                "penalty_id": appeal.penalty_id,
                "user_id": appeal.user_id,
                "username": username,
                "display_name": display_name,
                "reason": appeal.reason,
                "status": appeal.status,
                "created_at": appeal.created_at,
            }
            for appeal, username, display_name in appeals_with_users
        ], total
