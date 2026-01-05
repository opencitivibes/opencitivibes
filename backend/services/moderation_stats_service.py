"""
Service for moderation statistics.
"""

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from repositories.appeal_repository import AppealRepository
from repositories.flag_repository import FlagRepository
from repositories.penalty_repository import PenaltyRepository
from services.moderation_service import ModerationService

if TYPE_CHECKING:
    import models.schemas as schemas


class ModerationStatsService:
    """Service for moderation statistics."""

    @staticmethod
    def get_moderation_stats(db: Session) -> "schemas.ModerationStats":
        """
        Get comprehensive moderation statistics.

        Args:
            db: Database session

        Returns:
            ModerationStats schema with various moderation metrics
        """
        import models.schemas as schemas

        flag_repo = FlagRepository(db)
        penalty_repo = PenaltyRepository(db)
        appeal_repo = AppealRepository(db)

        # Flag stats
        total_flags = flag_repo.count_total_flags()
        pending_flags = flag_repo.count_pending_flags()
        resolved_today = flag_repo.count_resolved_today()
        flags_by_reason = flag_repo.get_flags_by_reason_stats()

        # Penalty stats
        active_penalties = penalty_repo.count_active_penalties()

        # Appeal stats
        pending_appeals = appeal_repo.count_pending_appeals()

        # Flags by day (last 30 days)
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        flags_by_day_raw = flag_repo.get_flags_by_day(start_date)
        flags_by_day = [
            {"date": str(date), "count": count} for date, count in flags_by_day_raw
        ]

        # Top flagged users - convert dicts to FlaggedUserSummary schemas
        flagged_users_raw, _ = ModerationService.get_flagged_users(db, skip=0, limit=10)
        flagged_users = [
            schemas.FlaggedUserSummary(**user) for user in flagged_users_raw
        ]

        return schemas.ModerationStats(
            total_flags=total_flags,
            pending_flags=pending_flags,
            resolved_today=resolved_today,
            flags_by_reason=flags_by_reason,
            flags_by_day=flags_by_day,
            top_flagged_users=flagged_users,
            active_penalties=active_penalties,
            pending_appeals=pending_appeals,
        )

    @staticmethod
    def get_admin_activity(
        db: Session,
        admin_id: int,
        days: int = 30,
    ) -> dict:
        """
        Get moderation activity for a specific admin.

        Args:
            db: Database session
            admin_id: ID of admin
            days: Number of days to look back

        Returns:
            Admin activity stats
        """
        flag_repo = FlagRepository(db)
        penalty_repo = PenaltyRepository(db)
        appeal_repo = AppealRepository(db)

        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Flag stats from repository
        flags_reviewed = flag_repo.count_flags_reviewed_by_admin(admin_id, start_date)
        flags_actioned = flag_repo.count_flags_actioned_by_admin(admin_id, start_date)
        flags_dismissed = flag_repo.count_flags_dismissed_by_admin(admin_id, start_date)

        # Penalty stats from repository
        penalties_issued = penalty_repo.count_penalties_issued_by_admin(
            admin_id, start_date
        )

        # Appeal stats from repository
        appeals_reviewed = appeal_repo.count_appeals_reviewed_by_admin(
            admin_id, start_date
        )

        return {
            "admin_id": admin_id,
            "period_days": days,
            "flags_reviewed": flags_reviewed,
            "flags_actioned": flags_actioned,
            "flags_dismissed": flags_dismissed,
            "penalties_issued": penalties_issued,
            "appeals_reviewed": appeals_reviewed,
        }
