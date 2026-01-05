"""Tests for RetentionService (Law 25 Compliance - Phase 3)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

import repositories.db_models as db_models
from authentication.auth import get_password_hash
from services.retention_service import RetentionMetrics, RetentionService


class TestRetentionServiceSoftDeleteCleanup:
    """Tests for soft-deleted content cleanup."""

    def test_cleanup_soft_deleted_ideas_past_retention(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ) -> None:
        """Ideas soft-deleted past retention period should be permanently deleted."""
        # Create idea soft-deleted 35 days ago (past 30 day retention)
        old_deleted = datetime.now(timezone.utc) - timedelta(days=35)
        idea = db_models.Idea(
            title="Old deleted idea",
            description="Should be permanently deleted after retention period.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
            deleted_at=old_deleted,
        )
        db_session.add(idea)
        db_session.commit()
        idea_id = idea.id

        # Run cleanup
        deleted_ideas, deleted_comments = RetentionService.cleanup_soft_deleted_content(
            db_session
        )

        assert deleted_ideas == 1
        assert deleted_comments == 0

        # Verify idea is gone
        remaining = db_session.query(db_models.Idea).filter_by(id=idea_id).first()
        assert remaining is None

    def test_cleanup_soft_deleted_ideas_within_retention(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ) -> None:
        """Ideas soft-deleted within retention period should be preserved."""
        # Create idea soft-deleted 15 days ago (within 30 day retention)
        recent_deleted = datetime.now(timezone.utc) - timedelta(days=15)
        idea = db_models.Idea(
            title="Recent deleted idea",
            description="Should be preserved within retention period.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
            deleted_at=recent_deleted,
        )
        db_session.add(idea)
        db_session.commit()
        idea_id = idea.id

        # Run cleanup
        deleted_ideas, deleted_comments = RetentionService.cleanup_soft_deleted_content(
            db_session
        )

        assert deleted_ideas == 0
        assert deleted_comments == 0

        # Verify idea still exists
        remaining = db_session.query(db_models.Idea).filter_by(id=idea_id).first()
        assert remaining is not None

    def test_cleanup_soft_deleted_comments_past_retention(
        self, db_session: Session, test_idea: db_models.Idea
    ) -> None:
        """Comments soft-deleted past retention period should be permanently deleted."""
        # Create comment soft-deleted 35 days ago
        old_deleted = datetime.now(timezone.utc) - timedelta(days=35)
        comment = db_models.Comment(
            content="Old deleted comment",
            idea_id=test_idea.id,
            user_id=test_idea.user_id,
            deleted_at=old_deleted,
        )
        db_session.add(comment)
        db_session.commit()
        comment_id = comment.id

        # Run cleanup
        deleted_ideas, deleted_comments = RetentionService.cleanup_soft_deleted_content(
            db_session
        )

        assert deleted_comments == 1

        # Verify comment is gone
        remaining = db_session.query(db_models.Comment).filter_by(id=comment_id).first()
        assert remaining is None

    def test_cleanup_cascades_to_related_records(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ) -> None:
        """Cleanup should cascade delete related votes, comments, and tags."""
        # Create idea with related records
        old_deleted = datetime.now(timezone.utc) - timedelta(days=35)
        idea = db_models.Idea(
            title="Idea with relations",
            description="Should cascade delete all related records.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
            deleted_at=old_deleted,
        )
        db_session.add(idea)
        db_session.commit()
        idea_id = idea.id

        # Add related vote
        vote = db_models.Vote(
            idea_id=idea_id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote)

        # Add related comment
        comment = db_models.Comment(
            content="Comment on idea",
            idea_id=idea_id,
            user_id=test_user.id,
        )
        db_session.add(comment)
        db_session.commit()

        # Run cleanup
        RetentionService.cleanup_soft_deleted_content(db_session)

        # Verify all related records are gone
        assert db_session.query(db_models.Idea).filter_by(id=idea_id).first() is None
        assert (
            db_session.query(db_models.Vote).filter_by(idea_id=idea_id).first() is None
        )
        assert (
            db_session.query(db_models.Comment).filter_by(idea_id=idea_id).first()
            is None
        )


class TestRetentionServiceLoginCodeCleanup:
    """Tests for expired login code cleanup."""

    def test_cleanup_expired_login_codes(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Expired login codes past retention should be deleted."""
        # Create expired code from 10 days ago (past 7 day retention)
        old_expiry = datetime.now(timezone.utc) - timedelta(days=10)
        code = db_models.EmailLoginCode(
            user_id=test_user.id,
            code_hash="0" * 64,  # SHA-256 hash placeholder
            expires_at=old_expiry,
        )
        db_session.add(code)
        db_session.commit()
        code_id = code.id

        # Run cleanup
        deleted_count = RetentionService.cleanup_expired_login_codes(db_session)

        assert deleted_count == 1
        assert (
            db_session.query(db_models.EmailLoginCode).filter_by(id=code_id).first()
            is None
        )

    def test_preserve_recent_expired_codes(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Recently expired codes within retention should be preserved for audit."""
        # Create code that expired 3 days ago (within 7 day retention)
        recent_expiry = datetime.now(timezone.utc) - timedelta(days=3)
        code = db_models.EmailLoginCode(
            user_id=test_user.id,
            code_hash="1" * 64,  # SHA-256 hash placeholder
            expires_at=recent_expiry,
        )
        db_session.add(code)
        db_session.commit()
        code_id = code.id

        # Run cleanup
        deleted_count = RetentionService.cleanup_expired_login_codes(db_session)

        assert deleted_count == 0
        assert (
            db_session.query(db_models.EmailLoginCode).filter_by(id=code_id).first()
            is not None
        )

    def test_preserve_valid_codes(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Valid (non-expired) codes should never be deleted."""
        # Create code that expires in the future
        future_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        code = db_models.EmailLoginCode(
            user_id=test_user.id,
            code_hash="2" * 64,  # SHA-256 hash placeholder
            expires_at=future_expiry,
        )
        db_session.add(code)
        db_session.commit()
        code_id = code.id

        # Run cleanup
        deleted_count = RetentionService.cleanup_expired_login_codes(db_session)

        assert deleted_count == 0
        assert (
            db_session.query(db_models.EmailLoginCode).filter_by(id=code_id).first()
            is not None
        )


class TestRetentionServiceInactiveAccounts:
    """Tests for inactive account processing."""

    def _create_inactive_user(
        self,
        db_session: Session,
        days_inactive: int,
        email: str = "inactive@example.com",
    ) -> db_models.User:
        """Helper to create an inactive user."""
        now = datetime.now(timezone.utc)
        last_activity = now - timedelta(days=days_inactive)
        user = db_models.User(
            email=email,
            username=f"inactive_{days_inactive}",
            display_name="Inactive User",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_global_admin=False,
            last_activity_at=last_activity,
            last_login_at=last_activity,
            consent_terms_accepted=True,
            consent_privacy_accepted=True,
            consent_terms_version="1.0",
            consent_privacy_version="1.0",
            consent_timestamp=last_activity,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def test_warn_inactive_users(self, db_session: Session) -> None:
        """Users inactive for 3+ years should receive warning."""
        # Create user inactive for 4 years
        user = self._create_inactive_user(db_session, days_inactive=365 * 4)

        # Run inactive account processing
        results = RetentionService.process_inactive_accounts(db_session)

        assert results["warnings_sent"] == 1
        assert results["accounts_anonymized"] == 0

        # Verify warning was marked
        db_session.refresh(user)
        assert user.inactivity_warning_sent_at is not None
        assert user.scheduled_anonymization_at is not None

    def test_no_warning_for_active_users(self, db_session: Session) -> None:
        """Users active within 3 years should not receive warning."""
        # Create user inactive for only 1 year
        user = self._create_inactive_user(
            db_session, days_inactive=365, email="active@example.com"
        )

        # Run inactive account processing
        results = RetentionService.process_inactive_accounts(db_session)

        assert results["warnings_sent"] == 0

        # Verify no warning sent
        db_session.refresh(user)
        assert user.inactivity_warning_sent_at is None

    def test_anonymize_after_grace_period(self, db_session: Session) -> None:
        """Users past grace period should be anonymized."""
        now = datetime.now(timezone.utc)
        # Create user who was warned 35 days ago (past 30 day grace)
        user = self._create_inactive_user(
            db_session, days_inactive=365 * 4, email="grace@example.com"
        )
        user.inactivity_warning_sent_at = now - timedelta(days=35)
        user.scheduled_anonymization_at = now - timedelta(days=5)  # Past due
        db_session.commit()

        # Run inactive account processing
        results = RetentionService.process_inactive_accounts(db_session)

        assert results["accounts_anonymized"] == 1

        # Verify user is anonymized
        db_session.refresh(user)
        assert user.is_active is False
        assert "deleted-user-" in user.email
        assert user.display_name == "Deleted User"

    def test_skip_already_warned_users(self, db_session: Session) -> None:
        """Users already warned should not receive duplicate warnings."""
        now = datetime.now(timezone.utc)
        user = self._create_inactive_user(
            db_session, days_inactive=365 * 4, email="warned@example.com"
        )
        user.inactivity_warning_sent_at = now - timedelta(days=10)  # Warned recently
        user.scheduled_anonymization_at = now + timedelta(days=20)  # Future date
        db_session.commit()

        # Run inactive account processing
        results = RetentionService.process_inactive_accounts(db_session)

        assert results["warnings_sent"] == 0
        assert results["accounts_anonymized"] == 0


class TestRetentionServiceConsentLogs:
    """Tests for consent log cleanup."""

    def test_cleanup_old_consent_logs_for_anonymized_users(
        self, db_session: Session
    ) -> None:
        """Old consent logs for deleted users should be cleaned up."""
        # Create anonymized user
        now = datetime.now(timezone.utc)
        old_date = now - timedelta(days=365 * 8)  # 8 years old
        user = db_models.User(
            email="deleted-user-12345@anonymized.local",
            username="deleted_12345",
            display_name="Deleted User",
            hashed_password="",
            is_active=False,
            consent_terms_accepted=False,
            consent_privacy_accepted=False,
        )
        db_session.add(user)
        db_session.commit()

        # Create old consent log for this user
        log = db_models.ConsentLog(
            user_id=user.id,
            consent_type="terms",
            action="accepted",
            policy_version="1.0",
            created_at=old_date,
        )
        db_session.add(log)
        db_session.commit()
        log_id = log.id

        # Run cleanup
        deleted_count = RetentionService.cleanup_old_consent_logs(db_session)

        assert deleted_count == 1
        assert (
            db_session.query(db_models.ConsentLog).filter_by(id=log_id).first() is None
        )

    def test_preserve_consent_logs_for_active_users(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Consent logs for active users should be preserved regardless of age."""
        now = datetime.now(timezone.utc)
        old_date = now - timedelta(days=365 * 10)  # Very old

        log = db_models.ConsentLog(
            user_id=test_user.id,
            consent_type="terms",
            action="accepted",
            policy_version="1.0",
            created_at=old_date,
        )
        db_session.add(log)
        db_session.commit()
        log_id = log.id

        # Run cleanup
        deleted_count = RetentionService.cleanup_old_consent_logs(db_session)

        assert deleted_count == 0
        assert (
            db_session.query(db_models.ConsentLog).filter_by(id=log_id).first()
            is not None
        )


class TestRetentionMetrics:
    """Tests for retention metrics endpoint."""

    def test_get_retention_status_empty_database(self, db_session: Session) -> None:
        """Metrics should work on empty database."""
        status = RetentionMetrics.get_retention_status(db_session)

        assert status["soft_deleted_ideas_pending"] == 0
        assert status["soft_deleted_ideas_ready_for_deletion"] == 0
        assert status["soft_deleted_comments_pending"] == 0
        assert status["soft_deleted_comments_ready_for_deletion"] == 0
        assert status["inactive_users_pending_warning"] == 0
        assert status["users_pending_anonymization"] == 0
        assert status["expired_login_codes"] == 0
        assert "retention_config" in status
        assert status["retention_config"]["soft_delete_retention_days"] == 30

    def test_get_retention_status_with_pending_items(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ) -> None:
        """Metrics should correctly count pending items."""
        now = datetime.now(timezone.utc)

        # Create soft-deleted idea within retention
        idea = db_models.Idea(
            title="Pending deletion",
            description="This idea is pending permanent deletion.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
            deleted_at=now - timedelta(days=10),  # Within retention
        )
        db_session.add(idea)

        # Create expired login code
        code = db_models.EmailLoginCode(
            user_id=test_user.id,
            code_hash="3" * 64,  # SHA-256 hash placeholder
            expires_at=now - timedelta(hours=1),  # Just expired
        )
        db_session.add(code)
        db_session.commit()

        status = RetentionMetrics.get_retention_status(db_session)

        assert status["soft_deleted_ideas_pending"] == 1
        assert status["soft_deleted_ideas_ready_for_deletion"] == 0
        assert status["expired_login_codes"] == 1


class TestRetentionServiceIntegration:
    """Integration tests for retention service."""

    def test_run_all_cleanup_jobs(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ) -> None:
        """run_all_cleanup_jobs should execute all cleanup routines."""
        now = datetime.now(timezone.utc)
        old_date = now - timedelta(days=35)

        # Create items that should be cleaned up
        idea = db_models.Idea(
            title="Old deleted idea",
            description="Should be cleaned up by run_all_cleanup_jobs.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
            deleted_at=old_date,
        )
        db_session.add(idea)

        code = db_models.EmailLoginCode(
            user_id=test_user.id,
            code_hash="4" * 64,  # SHA-256 hash placeholder
            expires_at=now - timedelta(days=10),
        )
        db_session.add(code)
        db_session.commit()

        # Run all cleanup jobs
        results = RetentionService.run_all_cleanup_jobs(db_session)

        assert "soft_deleted_content" in results
        assert "expired_login_codes" in results
        assert "inactive_accounts" in results

        # Verify cleanup happened
        assert results["soft_deleted_content"] == (1, 0)
        assert results["expired_login_codes"] == 1
