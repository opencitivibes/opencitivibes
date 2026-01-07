"""Tests for SecurityAuditService login event methods."""

from sqlalchemy.orm import Session

import repositories.db_models as db_models
from repositories.login_event_repository import LoginEventRepository
from services.security_audit_service import SecurityAuditService


class TestSecurityAuditServiceLogin:
    """Test cases for SecurityAuditService login event methods."""

    def test_log_login_success(self, db: Session, test_user: db_models.User):
        """Test logging a successful login."""
        event = SecurityAuditService.log_login_success(
            db=db,
            user_id=test_user.id,
            email=test_user.email,
            ip_address="192.168.1.1",
            user_agent="Test Browser",
        )

        assert event is not None
        assert event.event_type == db_models.LoginEventType.LOGIN_SUCCESS
        assert event.user_id == test_user.id
        assert event.email == test_user.email
        assert event.ip_address == "192.168.1.1"
        assert event.user_agent == "Test Browser"
        assert event.failure_reason is None

    def test_log_login_failure_invalid_password(
        self, db: Session, test_user: db_models.User
    ):
        """Test logging a failed login due to invalid password."""
        event = SecurityAuditService.log_login_failure(
            db=db,
            email=test_user.email,
            failure_reason=db_models.LoginFailureReason.INVALID_PASSWORD,
            ip_address="10.0.0.1",
            user_agent="Attack Bot",
            user_id=test_user.id,
        )

        assert event is not None
        assert event.event_type == db_models.LoginEventType.LOGIN_FAILED
        assert event.failure_reason == db_models.LoginFailureReason.INVALID_PASSWORD
        assert event.user_id == test_user.id

    def test_log_login_failure_user_not_found(self, db: Session):
        """Test logging a failed login for unknown user."""
        event = SecurityAuditService.log_login_failure(
            db=db,
            email="nonexistent@example.com",
            failure_reason=db_models.LoginFailureReason.USER_NOT_FOUND,
            ip_address="192.168.1.100",
        )

        assert event is not None
        assert event.event_type == db_models.LoginEventType.LOGIN_FAILED
        assert event.failure_reason == db_models.LoginFailureReason.USER_NOT_FOUND
        assert event.user_id is None
        assert event.email == "nonexistent@example.com"

    def test_log_logout(self, db: Session, test_user: db_models.User):
        """Test logging a logout event."""
        event = SecurityAuditService.log_logout(
            db=db,
            user_id=test_user.id,
            email=test_user.email,
            ip_address="192.168.1.1",
            user_agent="Test Browser",
        )

        assert event is not None
        assert event.event_type == db_models.LoginEventType.LOGOUT
        assert event.user_id == test_user.id

    def test_log_password_reset_request(self, db: Session, test_user: db_models.User):
        """Test logging a password reset request."""
        event = SecurityAuditService.log_password_reset_request(
            db=db,
            email=test_user.email,
            ip_address="192.168.1.1",
            user_agent="Test Browser",
            user_id=test_user.id,
        )

        assert event is not None
        assert event.event_type == db_models.LoginEventType.PASSWORD_RESET_REQUEST
        assert event.email == test_user.email

    def test_get_login_events_summary(self, db: Session, test_user: db_models.User):
        """Test getting login events summary."""
        # Create some events
        SecurityAuditService.log_login_success(
            db=db,
            user_id=test_user.id,
            email=test_user.email,
            ip_address="192.168.1.1",
        )
        SecurityAuditService.log_login_success(
            db=db,
            user_id=test_user.id,
            email=test_user.email,
            ip_address="192.168.1.2",
        )
        SecurityAuditService.log_login_failure(
            db=db,
            email="unknown@example.com",
            failure_reason=db_models.LoginFailureReason.USER_NOT_FOUND,
            ip_address="10.0.0.1",
        )

        summary = SecurityAuditService.get_login_events_summary(db)

        assert summary["total_events"] >= 3
        assert summary["successful_logins_24h"] >= 2
        assert summary["failed_logins_24h"] >= 1
        assert summary["unique_ips_24h"] >= 3
        assert "failed_login_rate" in summary
        assert "top_failure_reasons" in summary
        assert "generated_at" in summary

    def test_get_failed_attempts_for_email(self, db: Session):
        """Test counting failed attempts for email."""
        test_email = "target@example.com"

        # Create failures
        for _ in range(3):
            SecurityAuditService.log_login_failure(
                db=db,
                email=test_email,
                failure_reason=db_models.LoginFailureReason.INVALID_PASSWORD,
            )

        count = SecurityAuditService.get_failed_attempts_for_email(
            db=db, email=test_email
        )

        assert count == 3

    def test_get_failed_attempts_for_ip(self, db: Session):
        """Test counting failed attempts from IP."""
        test_ip = "10.20.30.40"

        # Create failures from same IP
        for i in range(4):
            SecurityAuditService.log_login_failure(
                db=db,
                email=f"user{i}@example.com",
                failure_reason=db_models.LoginFailureReason.INVALID_PASSWORD,
                ip_address=test_ip,
            )

        count = SecurityAuditService.get_failed_attempts_for_ip(
            db=db, ip_address=test_ip
        )

        assert count == 4


class TestLoginEventIntegration:
    """Integration tests for login event tracking with auth flow."""

    def test_login_success_creates_event(
        self, client, db: Session, test_user_with_password: db_models.User
    ):
        """Test that successful login creates a login event."""
        # Clear existing events
        repo = LoginEventRepository(db)
        initial_count = repo.count_events_in_window(
            window_hours=1, event_type=db_models.LoginEventType.LOGIN_SUCCESS
        )

        # Perform login
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user_with_password.email,
                "password": "TestPassword123!",
            },
        )

        assert response.status_code == 200

        # Check event was created
        new_count = repo.count_events_in_window(
            window_hours=1, event_type=db_models.LoginEventType.LOGIN_SUCCESS
        )
        assert new_count > initial_count

    def test_login_failure_creates_event(
        self, client, db: Session, test_user_with_password: db_models.User
    ):
        """Test that failed login creates a login event."""
        repo = LoginEventRepository(db)
        initial_count = repo.count_events_in_window(
            window_hours=1, event_type=db_models.LoginEventType.LOGIN_FAILED
        )

        # Perform failed login
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user_with_password.email,
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

        # Check event was created
        new_count = repo.count_events_in_window(
            window_hours=1, event_type=db_models.LoginEventType.LOGIN_FAILED
        )
        assert new_count > initial_count

    def test_login_failure_unknown_user_creates_event(self, client, db: Session):
        """Test that failed login for unknown user creates event."""
        repo = LoginEventRepository(db)
        initial_count = repo.count_events_in_window(
            window_hours=1, event_type=db_models.LoginEventType.LOGIN_FAILED
        )

        # Perform failed login with unknown email
        response = client.post(
            "/api/auth/login",
            data={"username": "nonexistent@example.com", "password": "anypassword"},
        )

        assert response.status_code == 401

        # Check event was created
        new_count = repo.count_events_in_window(
            window_hours=1, event_type=db_models.LoginEventType.LOGIN_FAILED
        )
        assert new_count > initial_count

        # Verify the reason is USER_NOT_FOUND
        events = repo.get_recent_events(
            event_type=db_models.LoginEventType.LOGIN_FAILED, limit=1
        )
        assert len(events) > 0
        assert events[0].failure_reason == db_models.LoginFailureReason.USER_NOT_FOUND
