"""
Unit tests for ModerationStatsService.
"""

from datetime import datetime, timedelta, timezone

from authentication.auth import get_password_hash
from repositories.db_models import (
    Appeal,
    AppealStatus,
    Comment,
    ContentFlag,
    ContentType,
    FlagReason,
    FlagStatus,
    PenaltyStatus,
    PenaltyType,
    User,
    UserPenalty,
)
from services.moderation_stats_service import ModerationStatsService


class TestModerationStatsServiceGetModerationStats:
    """Tests for ModerationStatsService.get_moderation_stats"""

    def test_get_moderation_stats_empty(self, db_session):
        """Test getting stats when there's no data."""
        stats = ModerationStatsService.get_moderation_stats(db_session)

        assert stats.total_flags == 0
        assert stats.pending_flags == 0
        assert stats.resolved_today == 0
        assert stats.flags_by_reason == {}
        assert stats.flags_by_day == []
        assert stats.top_flagged_users == []
        assert stats.active_penalties == 0
        assert stats.pending_appeals == 0

    def test_get_moderation_stats_with_flags(
        self, db_session, test_user, other_user, test_idea
    ):
        """Test getting stats with flag data."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create flags with different reasons
        flag1 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag1)

        reporter2 = User(
            email="reporter2@example.com",
            username="reporter2",
            display_name="Reporter 2",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_global_admin=False,
        )
        db_session.add(reporter2)
        db_session.commit()
        db_session.refresh(reporter2)

        flag2 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=reporter2.id,
            reason=FlagReason.HARASSMENT,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag2)
        db_session.commit()

        stats = ModerationStatsService.get_moderation_stats(db_session)

        assert stats.total_flags == 2
        assert stats.pending_flags == 2
        assert len(stats.flags_by_reason) == 2
        assert len(stats.top_flagged_users) == 1
        assert stats.top_flagged_users[0].user_id == test_user.id

    def test_get_moderation_stats_with_resolved_flags(
        self, db_session, test_user, other_user, admin_user, test_idea
    ):
        """Test stats include resolved flags from today."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create a resolved flag (using admin as reporter to avoid duplicate constraint)
        flag = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=admin_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.DISMISSED,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db_session.add(flag)
        db_session.commit()

        stats = ModerationStatsService.get_moderation_stats(db_session)

        assert stats.total_flags == 1
        assert stats.pending_flags == 0
        assert stats.resolved_today == 1

    def test_get_moderation_stats_with_penalties(
        self, db_session, test_user, admin_user
    ):
        """Test stats include active penalties."""
        # Create an active penalty
        penalty = UserPenalty(
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="Test penalty",
            issued_by=admin_user.id,
            status=PenaltyStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db_session.add(penalty)
        db_session.commit()

        stats = ModerationStatsService.get_moderation_stats(db_session)

        assert stats.active_penalties == 1

    def test_get_moderation_stats_with_appeals(self, db_session, test_user, admin_user):
        """Test stats include pending appeals."""
        # Create a penalty and appeal
        penalty = UserPenalty(
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="Test penalty",
            issued_by=admin_user.id,
            status=PenaltyStatus.APPEALED,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db_session.add(penalty)
        db_session.commit()
        db_session.refresh(penalty)

        appeal = Appeal(
            penalty_id=penalty.id,
            user_id=test_user.id,
            reason="I believe this penalty was issued in error. Please review.",
            status=AppealStatus.PENDING,
        )
        db_session.add(appeal)
        db_session.commit()

        stats = ModerationStatsService.get_moderation_stats(db_session)

        assert stats.pending_appeals == 1

    def test_get_moderation_stats_flags_by_day(
        self, db_session, test_user, other_user, test_idea
    ):
        """Test flags_by_day includes recent flags."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create flag today
        flag = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag)
        db_session.commit()

        stats = ModerationStatsService.get_moderation_stats(db_session)

        assert len(stats.flags_by_day) > 0
        # Should have at least one entry for today
        assert any(item["count"] == 1 for item in stats.flags_by_day)

    def test_get_moderation_stats_comprehensive(
        self, db_session, test_user, other_user, admin_user, test_idea
    ):
        """Test comprehensive stats with multiple data types."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create pending flag
        flag1 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag1)

        # Create resolved flag (using admin as reporter to avoid duplicate constraint)
        flag2 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=admin_user.id,
            reason=FlagReason.HARASSMENT,
            status=FlagStatus.DISMISSED,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db_session.add(flag2)

        # Create penalty
        penalty = UserPenalty(
            user_id=test_user.id,
            penalty_type=PenaltyType.WARNING,
            reason="Test penalty",
            issued_by=admin_user.id,
            status=PenaltyStatus.ACTIVE,
        )
        db_session.add(penalty)
        db_session.commit()
        db_session.refresh(penalty)

        # Create appeal
        appeal = Appeal(
            penalty_id=penalty.id,
            user_id=test_user.id,
            reason="I believe this penalty was issued in error. Please review.",
            status=AppealStatus.PENDING,
        )
        db_session.add(appeal)
        db_session.commit()

        stats = ModerationStatsService.get_moderation_stats(db_session)

        assert stats.total_flags == 2
        assert stats.pending_flags == 1
        assert stats.resolved_today == 1
        assert stats.active_penalties == 1
        assert stats.pending_appeals == 1
        assert len(stats.top_flagged_users) == 1


class TestModerationStatsServiceGetAdminActivity:
    """Tests for ModerationStatsService.get_admin_activity"""

    def test_get_admin_activity_no_activity(self, db_session, admin_user):
        """Test getting admin activity when admin has done nothing."""
        activity = ModerationStatsService.get_admin_activity(db_session, admin_user.id)

        assert activity["admin_id"] == admin_user.id
        assert activity["period_days"] == 30
        assert activity["flags_reviewed"] == 0
        assert activity["flags_actioned"] == 0
        assert activity["flags_dismissed"] == 0
        assert activity["penalties_issued"] == 0
        assert activity["appeals_reviewed"] == 0

    def test_get_admin_activity_with_flag_reviews(
        self, db_session, test_user, other_user, admin_user, test_idea
    ):
        """Test admin activity includes flag reviews."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create actioned flag
        flag1 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.ACTIONED,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db_session.add(flag1)

        # Create another comment for second flag
        comment2 = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment 2",
            is_moderated=False,
        )
        db_session.add(comment2)
        db_session.commit()
        db_session.refresh(comment2)

        # Create dismissed flag
        flag2 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment2.id,
            reporter_id=other_user.id,
            reason=FlagReason.HARASSMENT,
            status=FlagStatus.DISMISSED,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db_session.add(flag2)
        db_session.commit()

        activity = ModerationStatsService.get_admin_activity(db_session, admin_user.id)

        assert activity["flags_reviewed"] == 2
        assert activity["flags_actioned"] == 1
        assert activity["flags_dismissed"] == 1

    def test_get_admin_activity_with_penalties(self, db_session, test_user, admin_user):
        """Test admin activity includes penalties issued."""
        # Issue penalty
        penalty = UserPenalty(
            user_id=test_user.id,
            penalty_type=PenaltyType.WARNING,
            reason="Test penalty",
            issued_by=admin_user.id,
            status=PenaltyStatus.ACTIVE,
        )
        db_session.add(penalty)
        db_session.commit()

        activity = ModerationStatsService.get_admin_activity(db_session, admin_user.id)

        assert activity["penalties_issued"] == 1

    def test_get_admin_activity_with_appeals(self, db_session, test_user, admin_user):
        """Test admin activity includes appeals reviewed."""
        # Create penalty
        penalty = UserPenalty(
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="Test penalty",
            issued_by=admin_user.id,
            status=PenaltyStatus.REVOKED,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db_session.add(penalty)
        db_session.commit()
        db_session.refresh(penalty)

        # Create reviewed appeal
        appeal = Appeal(
            penalty_id=penalty.id,
            user_id=test_user.id,
            reason="I believe this penalty was issued in error. Please review.",
            status=AppealStatus.APPROVED,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db_session.add(appeal)
        db_session.commit()

        activity = ModerationStatsService.get_admin_activity(db_session, admin_user.id)

        assert activity["appeals_reviewed"] == 1

    def test_get_admin_activity_custom_period(self, db_session, test_user, admin_user):
        """Test admin activity with custom time period."""
        # Issue penalty
        penalty = UserPenalty(
            user_id=test_user.id,
            penalty_type=PenaltyType.WARNING,
            reason="Test penalty",
            issued_by=admin_user.id,
            status=PenaltyStatus.ACTIVE,
        )
        db_session.add(penalty)
        db_session.commit()

        # Get activity for last 7 days
        activity = ModerationStatsService.get_admin_activity(
            db_session, admin_user.id, days=7
        )

        assert activity["period_days"] == 7
        assert activity["penalties_issued"] == 1

    def test_get_admin_activity_filters_by_time(
        self, db_session, test_user, other_user, admin_user, test_idea
    ):
        """Test admin activity filters by time period."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create old flag (outside period)
        old_flag = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.DISMISSED,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc) - timedelta(days=100),
        )
        db_session.add(old_flag)
        db_session.commit()

        # Create another comment for recent flag (avoid duplicate constraint)
        comment2 = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment 2",
            is_moderated=False,
        )
        db_session.add(comment2)
        db_session.commit()
        db_session.refresh(comment2)

        # Create recent flag (within period)
        recent_flag = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment2.id,
            reporter_id=other_user.id,
            reason=FlagReason.HARASSMENT,
            status=FlagStatus.DISMISSED,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db_session.add(recent_flag)
        db_session.commit()

        # Get activity for last 30 days
        activity = ModerationStatsService.get_admin_activity(
            db_session, admin_user.id, days=30
        )

        # Should only count the recent flag
        assert activity["flags_reviewed"] == 1
        assert activity["flags_dismissed"] == 1

    def test_get_admin_activity_multiple_admins(
        self, db_session, test_user, admin_user, other_user
    ):
        """Test activity is isolated per admin."""
        # admin_user issues penalty
        penalty1 = UserPenalty(
            user_id=test_user.id,
            penalty_type=PenaltyType.WARNING,
            reason="Test penalty",
            issued_by=admin_user.id,
            status=PenaltyStatus.ACTIVE,
        )
        db_session.add(penalty1)

        # other_user (another admin) issues penalty
        penalty2 = UserPenalty(
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="Test penalty 2",
            issued_by=other_user.id,
            status=PenaltyStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db_session.add(penalty2)
        db_session.commit()

        # Get activity for admin_user
        activity = ModerationStatsService.get_admin_activity(db_session, admin_user.id)
        assert activity["penalties_issued"] == 1

        # Get activity for other_user
        activity = ModerationStatsService.get_admin_activity(db_session, other_user.id)
        assert activity["penalties_issued"] == 1

    def test_get_admin_activity_comprehensive(
        self, db_session, test_user, other_user, admin_user, test_idea
    ):
        """Test comprehensive admin activity with all types."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Review flag 1
        flag1 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.ACTIONED,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db_session.add(flag1)
        db_session.commit()

        # Create another comment for flag 2 (avoid duplicate constraint)
        comment2 = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment 2",
            is_moderated=False,
        )
        db_session.add(comment2)
        db_session.commit()
        db_session.refresh(comment2)

        # Review flag 2
        flag2 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment2.id,
            reporter_id=other_user.id,
            reason=FlagReason.HARASSMENT,
            status=FlagStatus.DISMISSED,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db_session.add(flag2)

        # Issue penalty
        penalty = UserPenalty(
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="Test penalty",
            issued_by=admin_user.id,
            status=PenaltyStatus.REVOKED,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db_session.add(penalty)
        db_session.commit()
        db_session.refresh(penalty)

        # Review appeal
        appeal = Appeal(
            penalty_id=penalty.id,
            user_id=test_user.id,
            reason="I believe this penalty was issued in error. Please review.",
            status=AppealStatus.APPROVED,
            reviewed_by=admin_user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        db_session.add(appeal)
        db_session.commit()

        activity = ModerationStatsService.get_admin_activity(db_session, admin_user.id)

        assert activity["flags_reviewed"] == 2
        assert activity["flags_actioned"] == 1
        assert activity["flags_dismissed"] == 1
        assert activity["penalties_issued"] == 1
        assert activity["appeals_reviewed"] == 1
