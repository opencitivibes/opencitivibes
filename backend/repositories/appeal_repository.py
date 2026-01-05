"""
Repository for appeal operations.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from repositories.base import BaseRepository
from repositories.db_models import Appeal, AppealStatus, User


class AppealRepository(BaseRepository[Appeal]):
    """Repository for appeal data access."""

    def __init__(self, db: Session):
        super().__init__(Appeal, db)

    def get_by_penalty(self, penalty_id: int) -> Optional[Appeal]:
        """Get appeal for a specific penalty."""
        return self.db.query(Appeal).filter(Appeal.penalty_id == penalty_id).first()

    def get_user_appeals(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Appeal]:
        """Get all appeals submitted by a user."""
        return (
            self.db.query(Appeal)
            .filter(Appeal.user_id == user_id)
            .order_by(Appeal.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_pending_appeals(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list, int]:
        """
        Get all pending appeals with user info.

        Returns:
            Tuple of (list of (appeal, username, display_name), total_count)
        """
        query = (
            self.db.query(Appeal, User.username, User.display_name)
            .join(User, Appeal.user_id == User.id)
            .filter(Appeal.status == AppealStatus.PENDING)
        )

        total = query.count()

        results = (
            query.order_by(Appeal.created_at.asc())  # Oldest first
            .offset(skip)
            .limit(limit)
            .all()
        )

        return results, total

    def update_appeal_status(
        self,
        appeal_id: int,
        status: AppealStatus,
        reviewer_id: int,
        review_notes: str,
    ) -> Optional[Appeal]:
        """
        Update appeal status with review.

        Args:
            appeal_id: ID of appeal
            status: New status (approved/rejected)
            reviewer_id: ID of reviewing admin
            review_notes: Review notes

        Returns:
            Updated appeal if found
        """
        appeal = self.get_by_id(appeal_id)
        if not appeal:
            return None

        appeal.status = status
        appeal.reviewed_at = datetime.now(timezone.utc)
        appeal.reviewed_by = reviewer_id
        appeal.review_notes = review_notes

        self.db.commit()
        self.db.refresh(appeal)
        return appeal

    def count_pending_appeals(self) -> int:
        """Get count of pending appeals."""
        result = (
            self.db.query(func.count(Appeal.id))
            .filter(Appeal.status == AppealStatus.PENDING)
            .scalar()
        )
        return result or 0

    def count_appeals_reviewed_by_admin(
        self, admin_id: int, start_date: datetime
    ) -> int:
        """
        Count appeals reviewed by an admin since start_date.

        Args:
            admin_id: Admin user ID
            start_date: Start date for the query

        Returns:
            Number of appeals reviewed
        """
        return (
            self.db.query(func.count(Appeal.id))
            .filter(
                Appeal.reviewed_by == admin_id,
                Appeal.reviewed_at >= start_date,
            )
            .scalar()
            or 0
        )
