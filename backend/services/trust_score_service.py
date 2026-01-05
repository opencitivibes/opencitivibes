"""
Service for user trust score calculations.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from repositories.db_models import User
from repositories.penalty_repository import PenaltyRepository


# Trust score constants
BASE_SCORE = 50
MAX_SCORE = 100
MIN_SCORE = 0

# Bonus caps
MAX_AGE_BONUS = 20
MAX_COMMENTS_BONUS = 15
MAX_REPORTER_BONUS = 10

# Scoring factors
DAYS_PER_AGE_POINT = 6  # 5 points per 30 days
COMMENTS_PER_POINT = 2  # 0.5 points per comment
REPORTER_POINTS_PER_FLAG = 2  # 2 points per validated flag report
VALID_FLAG_PENALTY = 10  # Points lost per valid flag received
ACTIVE_PENALTY_IMPACT = -20  # Impact of having active penalty


class TrustScoreService:
    """Service for trust score calculations and updates."""

    @staticmethod
    def calculate_trust_score(db: Session, user: User) -> int:
        """
        Calculate trust score for a user.

        Formula:
        - Base: 50
        - Account age bonus: +1 per 6 days (max +20)
        - Approved comments bonus: +0.5 per comment (max +15)
        - Successful flags submitted: +2 per flag (max +10)
        - Valid flags received: -10 per flag
        - Active penalty: -20

        Args:
            db: Database session
            user: User to calculate score for

        Returns:
            Trust score (0-100)
        """
        score = BASE_SCORE

        # Account age bonus
        # Handle both naive and timezone-aware datetimes
        user_created = user.created_at
        if user_created.tzinfo is None:
            # Assume naive datetime is UTC
            user_created = user_created.replace(tzinfo=timezone.utc)
        days_since_registration = (datetime.now(timezone.utc) - user_created).days
        age_bonus = min(MAX_AGE_BONUS, days_since_registration // DAYS_PER_AGE_POINT)
        score += age_bonus

        # Approved comments bonus
        comments_bonus = min(
            MAX_COMMENTS_BONUS,
            (user.approved_comments_count or 0) // COMMENTS_PER_POINT,
        )
        score += comments_bonus

        # Successful flag reports bonus
        reporter_bonus = min(
            MAX_REPORTER_BONUS,
            (user.flags_submitted_validated or 0) * REPORTER_POINTS_PER_FLAG,
        )
        score += reporter_bonus

        # Valid flags received penalty
        flags_penalty = (user.valid_flags_received or 0) * VALID_FLAG_PENALTY
        score -= flags_penalty

        # Active penalty impact
        penalty_repo = PenaltyRepository(db)
        active_penalty = penalty_repo.get_active_penalty(int(user.id))
        if active_penalty:
            score += ACTIVE_PENALTY_IMPACT

        # Clamp to valid range
        return max(MIN_SCORE, min(MAX_SCORE, score))

    @staticmethod
    def update_user_trust_score(db: Session, user_id: int) -> int:
        """
        Recalculate and update a user's trust score.

        Args:
            db: Database session
            user_id: ID of user to update

        Returns:
            New trust score
        """
        from repositories.user_repository import UserRepository

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            return 0

        new_score = TrustScoreService.calculate_trust_score(db, user)
        user.trust_score = new_score
        user_repo.commit()
        return new_score

    @staticmethod
    def increment_approved_comments(db: Session, user_id: int) -> None:
        """
        Increment approved comments count and update trust score.

        Called when a comment is approved.
        """
        from repositories.user_repository import UserRepository

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if user:
            user.approved_comments_count = (user.approved_comments_count or 0) + 1
            TrustScoreService.update_user_trust_score(db, user_id)

    @staticmethod
    def increment_flags_received(
        db: Session,
        user_id: int,
        is_valid: bool = False,
    ) -> None:
        """
        Increment flags received count and update trust score.

        Called when content receives a flag that leads to action.

        Args:
            db: Database session
            user_id: ID of content author
            is_valid: Whether flag led to content removal
        """
        from repositories.user_repository import UserRepository

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if user:
            if is_valid:
                user.valid_flags_received = (user.valid_flags_received or 0) + 1
            TrustScoreService.update_user_trust_score(db, user_id)

    @staticmethod
    def increment_successful_reports(db: Session, user_id: int) -> None:
        """
        Increment successful flag reports and update trust score.

        Called when a user's flag report leads to action.
        """
        from repositories.user_repository import UserRepository

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if user:
            user.flags_submitted_validated = (user.flags_submitted_validated or 0) + 1
            TrustScoreService.update_user_trust_score(db, user_id)

    @staticmethod
    def get_trust_level(score: int) -> str:
        """
        Get trust level label based on score.

        Args:
            score: Trust score (0-100)

        Returns:
            Trust level label
        """
        if score <= 20:
            return "low"
        elif score <= 40:
            return "below_average"
        elif score <= 60:
            return "average"
        elif score <= 80:
            return "good"
        else:
            return "excellent"

    @staticmethod
    def get_flag_weight(score: int) -> float:
        """
        Get flag weight multiplier based on trust score.

        Higher trust = flags count more.

        Args:
            score: Trust score

        Returns:
            Weight multiplier (0.5 to 1.5)
        """
        if score <= 20:
            return 0.5
        elif score <= 40:
            return 0.75
        elif score <= 60:
            return 1.0
        elif score <= 80:
            return 1.25
        else:
            return 1.5

    @staticmethod
    def requires_comment_approval(db: Session, user: User) -> bool:
        """
        Check if user's comments require approval.

        Admins never require approval.
        New users (< 5 approved comments) require approval.
        Low trust users always require approval.

        Args:
            db: Database session
            user: User to check

        Returns:
            True if approval required
        """
        # Admins never require approval
        if user.is_global_admin:
            return False

        # Explicit flag check
        if user.requires_comment_approval:
            return True

        # Low trust always requires approval
        score = TrustScoreService.calculate_trust_score(db, user)
        if score <= 40:
            return True

        # Check approved comments count
        if (user.approved_comments_count or 0) < 5:
            return True

        return False
