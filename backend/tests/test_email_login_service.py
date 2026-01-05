"""Tests for EmailLoginService."""

import pytest
from unittest.mock import patch

from services.email_login_service import EmailLoginService
from models.exceptions import (
    EmailLoginUserNotFoundException,
    EmailLoginRateLimitException,
    EmailLoginCodeExpiredException,
    EmailLoginCodeInvalidException,
    EmailLoginMaxAttemptsException,
    EmailDeliveryException,
)
from repositories.email_login_repository import EmailLoginCodeRepository


class TestEmailLoginService:
    """Test suite for EmailLoginService."""

    @patch("services.email_login_service.EmailService.send_login_code")
    def test_request_code_success(self, mock_send, db_session, test_user):
        """Should send code successfully."""
        mock_send.return_value = True

        expires_in = EmailLoginService.request_login_code(
            db=db_session,
            email=test_user.email,
        )

        assert expires_in > 0
        mock_send.assert_called_once()

    def test_request_code_unknown_email(self, db_session):
        """Should raise for unknown email."""
        with pytest.raises(EmailLoginUserNotFoundException):
            EmailLoginService.request_login_code(
                db=db_session,
                email="nonexistent@example.com",
            )

    @patch("services.email_login_service.EmailService.send_login_code")
    def test_request_code_rate_limit(self, mock_send, db_session, test_user):
        """Should enforce rate limit."""
        mock_send.return_value = True

        # Request max codes (3 per hour by default)
        for _ in range(3):
            EmailLoginService.request_login_code(
                db=db_session,
                email=test_user.email,
            )
            db_session.commit()

        # Next request should fail
        with pytest.raises(EmailLoginRateLimitException):
            EmailLoginService.request_login_code(
                db=db_session,
                email=test_user.email,
            )

    @patch("services.email_login_service.EmailService.send_login_code")
    def test_request_code_email_failure(self, mock_send, db_session, test_user):
        """Should raise if email fails."""
        mock_send.return_value = False

        with pytest.raises(EmailDeliveryException):
            EmailLoginService.request_login_code(
                db=db_session,
                email=test_user.email,
            )

    def test_verify_code_success(self, db_session, test_user):
        """Should verify valid code."""
        # Create code directly
        repo = EmailLoginCodeRepository(db_session)
        _, plain_code = repo.create_code(test_user.id)
        db_session.commit()

        token = EmailLoginService.verify_code(
            db=db_session,
            email=test_user.email,
            code=plain_code,
        )

        assert token.access_token is not None
        assert token.token_type == "bearer"

    def test_verify_code_wrong_code(self, db_session, test_user):
        """Should reject wrong code."""
        # Create code
        repo = EmailLoginCodeRepository(db_session)
        repo.create_code(test_user.id)
        db_session.commit()

        with pytest.raises(EmailLoginCodeInvalidException):
            EmailLoginService.verify_code(
                db=db_session,
                email=test_user.email,
                code="000000",
            )

    def test_verify_code_no_code(self, db_session, test_user):
        """Should raise if no code exists."""
        with pytest.raises(EmailLoginCodeExpiredException):
            EmailLoginService.verify_code(
                db=db_session,
                email=test_user.email,
                code="123456",
            )

    def test_verify_code_tracks_attempts(self, db_session, test_user):
        """Should track failed attempts."""
        repo = EmailLoginCodeRepository(db_session)
        repo.create_code(test_user.id)
        db_session.commit()

        # With MAX_ATTEMPTS=5, we should get 4 Invalid exceptions
        # then the 5th attempt triggers MaxAttempts
        # Note: Service commits after each attempt, no need for extra commit
        for i in range(4):
            with pytest.raises(EmailLoginCodeInvalidException):
                EmailLoginService.verify_code(
                    db=db_session,
                    email=test_user.email,
                    code="000000",
                )

        # 5th attempt should hit max attempts
        with pytest.raises(EmailLoginMaxAttemptsException):
            EmailLoginService.verify_code(
                db=db_session,
                email=test_user.email,
                code="000000",
            )

    def test_verify_code_unknown_email(self, db_session):
        """Should raise for unknown email."""
        with pytest.raises(EmailLoginUserNotFoundException):
            EmailLoginService.verify_code(
                db=db_session,
                email="nonexistent@example.com",
                code="123456",
            )

    def test_verify_code_inactive_user(self, db_session, test_user):
        """Should raise for inactive user."""
        # Create code first
        repo = EmailLoginCodeRepository(db_session)
        _, plain_code = repo.create_code(test_user.id)
        db_session.commit()

        # Deactivate user
        test_user.is_active = False
        db_session.commit()

        with pytest.raises(EmailLoginUserNotFoundException):
            EmailLoginService.verify_code(
                db=db_session,
                email=test_user.email,
                code=plain_code,
            )

    def test_check_pending_code_exists(self, db_session, test_user):
        """Should return seconds until expiry for pending code."""
        repo = EmailLoginCodeRepository(db_session)
        repo.create_code(test_user.id)
        db_session.commit()

        remaining = EmailLoginService.check_pending_code(db_session, test_user.email)

        assert remaining is not None
        assert remaining > 0

    def test_check_pending_code_none(self, db_session, test_user):
        """Should return None when no pending code."""
        remaining = EmailLoginService.check_pending_code(db_session, test_user.email)

        assert remaining is None

    def test_check_pending_code_unknown_email(self, db_session):
        """Should return None for unknown email."""
        remaining = EmailLoginService.check_pending_code(
            db_session, "nonexistent@example.com"
        )

        assert remaining is None

    def test_cleanup_expired_codes(self, db_session, test_user):
        """Should cleanup expired codes."""
        from datetime import datetime, timedelta, timezone

        repo = EmailLoginCodeRepository(db_session)

        # Create and expire a code
        code_record, _ = repo.create_code(test_user.id)
        code_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=25)
        db_session.commit()

        count = EmailLoginService.cleanup_expired_codes(db_session, older_than_hours=24)

        assert count == 1

    @patch("services.email_login_service.EmailService.send_login_code")
    def test_request_code_with_ip_address(self, mock_send, db_session, test_user):
        """Should store IP address with code."""
        mock_send.return_value = True

        EmailLoginService.request_login_code(
            db=db_session,
            email=test_user.email,
            ip_address="192.168.1.100",
        )

        repo = EmailLoginCodeRepository(db_session)
        active = repo.get_active_code_for_user(test_user.id)

        assert active is not None
        assert active.ip_address == "192.168.1.100"

    @patch("services.email_login_service.EmailService.send_login_code")
    def test_request_code_with_language(self, mock_send, db_session, test_user):
        """Should pass language to email service."""
        mock_send.return_value = True

        EmailLoginService.request_login_code(
            db=db_session,
            email=test_user.email,
            language="fr",
        )

        # Verify email was called with French language
        call_args = mock_send.call_args
        assert call_args.kwargs["language"] == "fr"

    def test_request_code_inactive_user(self, db_session, test_user):
        """Inactive users should not be able to request codes."""
        test_user.is_active = False
        db_session.commit()

        with pytest.raises(EmailLoginUserNotFoundException):
            EmailLoginService.request_login_code(
                db=db_session,
                email=test_user.email,
            )
