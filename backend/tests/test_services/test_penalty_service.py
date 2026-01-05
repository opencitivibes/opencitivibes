"""
Unit tests for PenaltyService.
"""

from datetime import datetime, timezone

import pytest

from models.exceptions import (
    CannotRevokePenaltyException,
    PenaltyNotFoundException,
    UserAlreadyPenalizedException,
    UserNotFoundException,
)
from repositories.db_models import PenaltyStatus, PenaltyType
from services.penalty_service import PenaltyService


class TestPenaltyServiceIssuePenalty:
    """Tests for PenaltyService.issue_penalty"""

    def test_issue_warning_success(self, db_session, test_user, admin_user):
        """Test successfully issuing a warning."""
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.WARNING,
            reason="First violation of community guidelines",
            issued_by=admin_user.id,
        )

        assert penalty is not None
        assert penalty.user_id == test_user.id
        assert penalty.penalty_type == PenaltyType.WARNING
        assert penalty.status == PenaltyStatus.ACTIVE
        assert penalty.issued_by == admin_user.id
        # Warnings have no expiration
        assert penalty.expires_at is None

    def test_issue_temp_ban_24h_success(self, db_session, test_user, admin_user):
        """Test successfully issuing a 24h temporary ban."""
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="Repeated violations - 24h ban",
            issued_by=admin_user.id,
        )

        assert penalty is not None
        assert penalty.penalty_type == PenaltyType.TEMP_BAN_24H
        assert penalty.expires_at is not None
        # Should expire in approximately 24 hours
        # Handle naive datetime from SQLite
        expires_at = penalty.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        time_diff = expires_at - datetime.now(timezone.utc)
        assert 23 <= time_diff.total_seconds() / 3600 <= 25

    def test_issue_permanent_ban_success(self, db_session, test_user, admin_user):
        """Test successfully issuing a permanent ban."""
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.PERMANENT_BAN,
            reason="Severe violation - permanent ban",
            issued_by=admin_user.id,
        )

        assert penalty is not None
        assert penalty.penalty_type == PenaltyType.PERMANENT_BAN
        assert penalty.expires_at is None  # Permanent, no expiration

    def test_issue_penalty_user_not_found(self, db_session, admin_user):
        """Test issuing penalty to non-existent user fails."""
        with pytest.raises(UserNotFoundException):
            PenaltyService.issue_penalty(
                db=db_session,
                user_id=99999,
                penalty_type=PenaltyType.WARNING,
                reason="Test penalty",
                issued_by=admin_user.id,
            )

    def test_issue_penalty_already_has_equal_penalty(
        self, db_session, test_user, admin_user
    ):
        """Test issuing same-level penalty fails."""
        # Issue first warning
        PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.WARNING,
            reason="First warning",
            issued_by=admin_user.id,
        )

        # Try to issue another warning
        with pytest.raises(UserAlreadyPenalizedException):
            PenaltyService.issue_penalty(
                db=db_session,
                user_id=test_user.id,
                penalty_type=PenaltyType.WARNING,
                reason="Second warning",
                issued_by=admin_user.id,
            )

    def test_issue_higher_penalty_succeeds(self, db_session, test_user, admin_user):
        """Test issuing higher-level penalty when lower exists succeeds."""
        # Issue warning
        PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.WARNING,
            reason="Warning",
            issued_by=admin_user.id,
        )

        # Issue 24h ban (higher severity)
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="Escalated to 24h ban",
            issued_by=admin_user.id,
        )

        assert penalty.penalty_type == PenaltyType.TEMP_BAN_24H

    def test_issue_penalty_with_related_flags(self, db_session, test_user, admin_user):
        """Test issuing penalty with related flag IDs."""
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.WARNING,
            reason="Based on flags",
            issued_by=admin_user.id,
            related_flag_ids=[1, 2, 3],
        )

        assert penalty.related_flag_ids is not None
        assert "1" in penalty.related_flag_ids


class TestPenaltyServiceCheckBanned:
    """Tests for PenaltyService.check_user_banned"""

    def test_user_not_banned_no_penalties(self, db_session, test_user):
        """Test user with no penalties is not banned."""
        result = PenaltyService.check_user_banned(db_session, test_user.id)
        assert result is None

    def test_user_not_banned_only_warning(self, db_session, test_user, admin_user):
        """Test user with only a warning is not banned."""
        PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.WARNING,
            reason="Warning only",
            issued_by=admin_user.id,
        )

        result = PenaltyService.check_user_banned(db_session, test_user.id)
        assert result is None  # Warnings don't count as bans

    def test_user_banned_with_temp_ban(self, db_session, test_user, admin_user):
        """Test user with temp ban is banned."""
        PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="24h ban",
            issued_by=admin_user.id,
        )

        result = PenaltyService.check_user_banned(db_session, test_user.id)
        assert result is not None
        assert result.penalty_type == PenaltyType.TEMP_BAN_24H

    def test_user_banned_with_permanent_ban(self, db_session, test_user, admin_user):
        """Test user with permanent ban is banned."""
        PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.PERMANENT_BAN,
            reason="Permanent",
            issued_by=admin_user.id,
        )

        result = PenaltyService.check_user_banned(db_session, test_user.id)
        assert result is not None
        assert result.penalty_type == PenaltyType.PERMANENT_BAN


class TestPenaltyServiceRevokePenalty:
    """Tests for PenaltyService.revoke_penalty"""

    def test_revoke_penalty_success(self, db_session, test_user, admin_user):
        """Test successfully revoking a penalty."""
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="24h ban",
            issued_by=admin_user.id,
        )

        revoked = PenaltyService.revoke_penalty(
            db=db_session,
            penalty_id=penalty.id,
            revoked_by=admin_user.id,
            reason="Appeal approved",
        )

        assert revoked is not None
        assert revoked.status == PenaltyStatus.REVOKED
        assert revoked.revoked_at is not None
        assert revoked.revoked_by == admin_user.id
        assert revoked.revoke_reason == "Appeal approved"

    def test_revoke_penalty_not_found(self, db_session, admin_user):
        """Test revoking non-existent penalty fails."""
        with pytest.raises(PenaltyNotFoundException):
            PenaltyService.revoke_penalty(
                db=db_session,
                penalty_id=99999,
                revoked_by=admin_user.id,
                reason="Test",
            )

    def test_revoke_already_revoked_penalty(self, db_session, test_user, admin_user):
        """Test revoking already revoked penalty fails."""
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="24h ban",
            issued_by=admin_user.id,
        )

        # Revoke once
        PenaltyService.revoke_penalty(
            db=db_session,
            penalty_id=penalty.id,
            revoked_by=admin_user.id,
            reason="First revoke",
        )

        # Try to revoke again
        with pytest.raises(CannotRevokePenaltyException):
            PenaltyService.revoke_penalty(
                db=db_session,
                penalty_id=penalty.id,
                revoked_by=admin_user.id,
                reason="Second revoke",
            )


class TestPenaltyServiceProgression:
    """Tests for penalty progression logic."""

    def test_get_next_penalty_no_history(self, db_session, test_user):
        """Test next penalty for user with no history is warning."""
        next_type = PenaltyService.get_next_penalty_type(db_session, test_user.id)
        assert next_type == PenaltyType.WARNING

    def test_get_next_penalty_after_warning(self, db_session, test_user, admin_user):
        """Test next penalty after warning is 24h ban."""
        # Issue warning
        PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.WARNING,
            reason="Warning",
            issued_by=admin_user.id,
        )

        next_type = PenaltyService.get_next_penalty_type(db_session, test_user.id)
        assert next_type == PenaltyType.TEMP_BAN_24H


class TestPenaltyServiceCanAppeal:
    """Tests for PenaltyService.can_appeal"""

    def test_can_appeal_active_temp_ban(self, db_session, test_user, admin_user):
        """Test active temp ban can be appealed."""
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="24h ban",
            issued_by=admin_user.id,
        )

        assert PenaltyService.can_appeal(penalty) is True

    def test_cannot_appeal_warning(self, db_session, test_user, admin_user):
        """Test warnings cannot be appealed."""
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.WARNING,
            reason="Warning",
            issued_by=admin_user.id,
        )

        assert PenaltyService.can_appeal(penalty) is False

    def test_cannot_appeal_revoked_penalty(self, db_session, test_user, admin_user):
        """Test revoked penalties cannot be appealed."""
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="24h ban",
            issued_by=admin_user.id,
        )

        PenaltyService.revoke_penalty(
            db=db_session,
            penalty_id=penalty.id,
            revoked_by=admin_user.id,
            reason="Revoked",
        )

        db_session.refresh(penalty)
        assert PenaltyService.can_appeal(penalty) is False
