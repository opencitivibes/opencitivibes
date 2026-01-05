"""
Unit tests for AppealService.
"""

import pytest

from models.exceptions import (
    AppealAlreadyExistsException,
    AppealNotFoundException,
    CannotAppealException,
    PenaltyNotFoundException,
)
from repositories.db_models import AppealStatus, PenaltyStatus, PenaltyType
from services.appeal_service import AppealService
from services.penalty_service import PenaltyService


class TestAppealServiceSubmitAppeal:
    """Tests for AppealService.submit_appeal"""

    def test_submit_appeal_success(self, db_session, test_user, admin_user):
        """Test successfully submitting an appeal."""
        # Issue a temp ban
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="24h ban for testing",
            issued_by=admin_user.id,
        )

        # Submit appeal
        appeal = AppealService.submit_appeal(
            db=db_session,
            penalty_id=penalty.id,
            user_id=test_user.id,
            reason="I believe this penalty was issued in error. I was not violating any rules.",
        )

        assert appeal is not None
        assert appeal.penalty_id == penalty.id
        assert appeal.user_id == test_user.id
        assert appeal.status == AppealStatus.PENDING
        assert "I believe" in appeal.reason

        # Penalty should be marked as appealed
        db_session.refresh(penalty)
        assert penalty.status == PenaltyStatus.APPEALED

    def test_submit_appeal_penalty_not_found(self, db_session, test_user):
        """Test submitting appeal for non-existent penalty fails."""
        with pytest.raises(PenaltyNotFoundException):
            AppealService.submit_appeal(
                db=db_session,
                penalty_id=99999,
                user_id=test_user.id,
                reason="This is my appeal reason that is long enough for validation.",
            )

    def test_submit_appeal_not_owner(
        self, db_session, test_user, other_user, admin_user
    ):
        """Test submitting appeal for someone else's penalty fails."""
        # Issue penalty to test_user
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="24h ban",
            issued_by=admin_user.id,
        )

        # other_user tries to appeal test_user's penalty
        with pytest.raises(PenaltyNotFoundException):
            AppealService.submit_appeal(
                db=db_session,
                penalty_id=penalty.id,
                user_id=other_user.id,
                reason="This is my appeal reason that is long enough for validation.",
            )

    def test_submit_appeal_warning_fails(self, db_session, test_user, admin_user):
        """Test submitting appeal for a warning fails."""
        # Issue a warning
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.WARNING,
            reason="Warning",
            issued_by=admin_user.id,
        )

        # Try to appeal the warning
        with pytest.raises(CannotAppealException):
            AppealService.submit_appeal(
                db=db_session,
                penalty_id=penalty.id,
                user_id=test_user.id,
                reason="This is my appeal reason that is long enough for validation.",
            )

    def test_submit_appeal_duplicate_fails(self, db_session, test_user, admin_user):
        """Test submitting duplicate appeal fails."""
        # Issue penalty
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="24h ban",
            issued_by=admin_user.id,
        )

        # First appeal succeeds
        AppealService.submit_appeal(
            db=db_session,
            penalty_id=penalty.id,
            user_id=test_user.id,
            reason="First appeal reason that is long enough for validation purposes.",
        )

        # Second appeal fails
        with pytest.raises(AppealAlreadyExistsException):
            AppealService.submit_appeal(
                db=db_session,
                penalty_id=penalty.id,
                user_id=test_user.id,
                reason="Second appeal reason that is long enough for validation purposes.",
            )


class TestAppealServiceReviewAppeal:
    """Tests for AppealService.review_appeal"""

    def test_approve_appeal_success(self, db_session, test_user, admin_user):
        """Test successfully approving an appeal."""
        # Issue penalty
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="24h ban",
            issued_by=admin_user.id,
        )

        # Submit appeal
        appeal = AppealService.submit_appeal(
            db=db_session,
            penalty_id=penalty.id,
            user_id=test_user.id,
            reason="This is my appeal reason that is long enough for validation purposes.",
        )

        # Approve appeal
        reviewed = AppealService.review_appeal(
            db=db_session,
            appeal_id=appeal.id,
            reviewer_id=admin_user.id,
            action="approve",
            review_notes="Appeal approved after review.",
        )

        assert reviewed is not None
        assert reviewed.status == AppealStatus.APPROVED
        assert reviewed.reviewed_at is not None
        assert reviewed.reviewed_by == admin_user.id
        assert "approved" in (reviewed.review_notes or "")

        # Penalty should be revoked
        db_session.refresh(penalty)
        assert penalty.status == PenaltyStatus.REVOKED

    def test_reject_appeal_success(self, db_session, test_user, admin_user):
        """Test successfully rejecting an appeal."""
        # Issue penalty
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="24h ban",
            issued_by=admin_user.id,
        )

        # Submit appeal
        appeal = AppealService.submit_appeal(
            db=db_session,
            penalty_id=penalty.id,
            user_id=test_user.id,
            reason="This is my appeal reason that is long enough for validation purposes.",
        )

        # Reject appeal
        reviewed = AppealService.review_appeal(
            db=db_session,
            appeal_id=appeal.id,
            reviewer_id=admin_user.id,
            action="reject",
            review_notes="Appeal rejected - violation confirmed.",
        )

        assert reviewed is not None
        assert reviewed.status == AppealStatus.REJECTED
        assert "rejected" in (reviewed.review_notes or "")

        # Penalty should be reactivated
        db_session.refresh(penalty)
        assert penalty.status == PenaltyStatus.ACTIVE

    def test_review_appeal_not_found(self, db_session, admin_user):
        """Test reviewing non-existent appeal fails."""
        with pytest.raises(AppealNotFoundException):
            AppealService.review_appeal(
                db=db_session,
                appeal_id=99999,
                reviewer_id=admin_user.id,
                action="approve",
                review_notes="Test",
            )

    def test_review_already_reviewed_appeal(self, db_session, test_user, admin_user):
        """Test reviewing already-reviewed appeal fails."""
        # Issue penalty and submit appeal
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="24h ban",
            issued_by=admin_user.id,
        )

        appeal = AppealService.submit_appeal(
            db=db_session,
            penalty_id=penalty.id,
            user_id=test_user.id,
            reason="This is my appeal reason that is long enough for validation purposes.",
        )

        # Review once
        AppealService.review_appeal(
            db=db_session,
            appeal_id=appeal.id,
            reviewer_id=admin_user.id,
            action="approve",
            review_notes="First review",
        )

        # Try to review again
        with pytest.raises(AppealNotFoundException):
            AppealService.review_appeal(
                db=db_session,
                appeal_id=appeal.id,
                reviewer_id=admin_user.id,
                action="reject",
                review_notes="Second review",
            )


class TestAppealServiceGetAppeals:
    """Tests for AppealService getter methods."""

    def test_get_user_appeals(self, db_session, test_user, admin_user):
        """Test getting appeals for a user."""
        # Issue penalty and submit appeal
        penalty = PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="24h ban",
            issued_by=admin_user.id,
        )

        AppealService.submit_appeal(
            db=db_session,
            penalty_id=penalty.id,
            user_id=test_user.id,
            reason="This is my appeal reason that is long enough for validation purposes.",
        )

        # Get user's appeals
        appeals = AppealService.get_user_appeals(db_session, test_user.id)

        assert len(appeals) == 1
        assert appeals[0].user_id == test_user.id

    def test_get_pending_appeals(self, db_session, test_user, other_user, admin_user):
        """Test getting pending appeals for admin review."""
        # Issue penalties and submit appeals for two users
        for user in [test_user, other_user]:
            penalty = PenaltyService.issue_penalty(
                db=db_session,
                user_id=user.id,
                penalty_type=PenaltyType.TEMP_BAN_24H,
                reason="24h ban",
                issued_by=admin_user.id,
            )

            AppealService.submit_appeal(
                db=db_session,
                penalty_id=penalty.id,
                user_id=user.id,
                reason="This is my appeal reason that is long enough for validation purposes.",
            )

        # Get pending appeals
        appeals, total = AppealService.get_pending_appeals(db_session)

        assert total == 2
        assert len(appeals) == 2
        # Each appeal should have user info
        assert all("username" in a for a in appeals)
