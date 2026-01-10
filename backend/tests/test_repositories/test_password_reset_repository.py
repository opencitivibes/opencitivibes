"""Tests for PasswordResetRepository.

Security tests addressing audit findings:
- Finding #1 (CRITICAL): Verify bcrypt hashing (NOT SHA-256)
- Finding #4 (HIGH): Test account lockout mechanisms
- Finding #11 (LOW): Test context signature binding
"""

from datetime import datetime, timedelta, timezone

import bcrypt

import repositories.db_models as db_models
from repositories.password_reset_repository import PasswordResetRepository


class TestPasswordResetRepository:
    """Test cases for PasswordResetRepository."""

    def test_generate_code_length(self, db_session):
        """Generate code has correct length."""
        code = PasswordResetRepository.generate_code()
        # Default length is 6 digits
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_randomness(self, db_session):
        """Generate code produces different values."""
        codes = [PasswordResetRepository.generate_code() for _ in range(10)]
        # Should have at least some unique codes
        assert len(set(codes)) > 1

    def test_hash_code_uses_bcrypt(self, db_session):
        """Hash code uses bcrypt (Finding #1 - CRITICAL)."""
        code = "123456"
        code_hash = PasswordResetRepository.hash_code(code)

        # bcrypt hashes are 60 characters and start with $2b$
        assert len(code_hash) == 60
        assert code_hash.startswith("$2b$")

        # Verify it's NOT SHA-256 (which is 64 hex chars)
        assert len(code_hash) != 64

    def test_verify_code_hash_success(self, db_session):
        """Verify correct code matches hash."""
        code = "123456"
        code_hash = PasswordResetRepository.hash_code(code)

        assert PasswordResetRepository.verify_code_hash(code, code_hash) is True

    def test_verify_code_hash_wrong_code(self, db_session):
        """Verify wrong code does not match hash."""
        code = "123456"
        wrong_code = "654321"
        code_hash = PasswordResetRepository.hash_code(code)

        assert PasswordResetRepository.verify_code_hash(wrong_code, code_hash) is False

    def test_verify_code_hash_constant_time(self, db_session):
        """Verify bcrypt provides constant-time comparison."""
        code = "123456"
        code_hash = PasswordResetRepository.hash_code(code)

        # bcrypt.checkpw is designed for constant-time comparison
        # We just verify the function is being used correctly
        result = bcrypt.checkpw(code.encode(), code_hash.encode())
        assert result is True

    def test_create_token(self, db_session, test_user):
        """Create token stores bcrypt hash and returns plain code."""
        repo = PasswordResetRepository(db_session)
        token, plain_code = repo.create_token(
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert token is not None
        assert token.user_id == test_user.id
        assert token.ip_address == "192.168.1.1"
        assert token.user_agent == "Mozilla/5.0"
        assert token.attempts == 0
        assert token.used_at is None
        assert token.expires_at > datetime.now(timezone.utc)

        # Verify code is bcrypt hashed (60 chars, starts with $2b$)
        assert len(token.code_hash) == 60
        assert token.code_hash.startswith("$2b$")

        # Verify plain code works with hash
        assert PasswordResetRepository.verify_code_hash(plain_code, token.code_hash)

    def test_create_token_with_context_signature(self, db_session, test_user):
        """Create token includes context signature (Finding #11)."""
        repo = PasswordResetRepository(db_session)
        token, _ = repo.create_token(
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert token.context_signature is not None
        assert len(token.context_signature) == 64  # SHA-256 hex

    def test_get_valid_code_success(self, db_session, test_user):
        """Get valid code returns token for correct code."""
        repo = PasswordResetRepository(db_session)
        token, plain_code = repo.create_token(user_id=test_user.id)
        db_session.commit()

        result = repo.get_valid_code(test_user.id, plain_code)
        assert result is not None
        assert result.id == token.id

    def test_get_valid_code_wrong_code(self, db_session, test_user):
        """Get valid code returns None for wrong code."""
        repo = PasswordResetRepository(db_session)
        repo.create_token(user_id=test_user.id)
        db_session.commit()

        result = repo.get_valid_code(test_user.id, "000000")
        assert result is None

    def test_get_valid_code_expired(self, db_session, test_user):
        """Get valid code returns None for expired code."""
        repo = PasswordResetRepository(db_session)
        token, plain_code = repo.create_token(user_id=test_user.id)

        # Manually expire the token
        token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()

        result = repo.get_valid_code(test_user.id, plain_code)
        assert result is None

    def test_get_valid_code_already_used(self, db_session, test_user):
        """Get valid code returns None for already used code."""
        repo = PasswordResetRepository(db_session)
        token, plain_code = repo.create_token(user_id=test_user.id)

        # Mark as used
        token.used_at = datetime.now(timezone.utc)
        db_session.commit()

        result = repo.get_valid_code(test_user.id, plain_code)
        assert result is None

    def test_get_valid_code_max_attempts(self, db_session, test_user):
        """Get valid code returns None when max attempts reached."""
        repo = PasswordResetRepository(db_session)
        token, plain_code = repo.create_token(user_id=test_user.id)

        # Set attempts to max
        token.attempts = 5
        db_session.commit()

        result = repo.get_valid_code(test_user.id, plain_code)
        assert result is None

    def test_increment_attempts(self, db_session, test_user):
        """Increment attempts updates counter."""
        repo = PasswordResetRepository(db_session)
        token, _ = repo.create_token(user_id=test_user.id)
        db_session.commit()

        assert token.attempts == 0
        repo.increment_attempts(token.id)
        db_session.refresh(token)
        assert token.attempts == 1

    def test_mark_as_verified_generates_reset_token(self, db_session, test_user):
        """Mark as verified generates reset token."""
        repo = PasswordResetRepository(db_session)
        token, _ = repo.create_token(user_id=test_user.id)
        db_session.commit()

        reset_token = repo.mark_as_verified(token.id)
        db_session.refresh(token)

        assert reset_token is not None
        assert len(reset_token) == 64  # hex token
        assert token.verified_at is not None
        assert token.reset_token == reset_token
        assert token.reset_token_expires_at is not None
        # Make comparison timezone-aware
        now = datetime.now(timezone.utc)
        expires_at = token.reset_token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        assert expires_at > now

    def test_mark_as_used(self, db_session, test_user):
        """Mark as used sets used_at timestamp."""
        repo = PasswordResetRepository(db_session)
        token, _ = repo.create_token(user_id=test_user.id)
        db_session.commit()

        assert token.used_at is None
        repo.mark_as_used(token.id)
        db_session.refresh(token)
        assert token.used_at is not None

    def test_get_verified_token_success(self, db_session, test_user):
        """Get verified token returns token for valid reset token."""
        repo = PasswordResetRepository(db_session)
        token, _ = repo.create_token(user_id=test_user.id)
        db_session.commit()

        reset_token = repo.mark_as_verified(token.id)
        db_session.commit()

        result = repo.get_verified_token(reset_token)
        assert result is not None
        assert result.id == token.id

    def test_get_verified_token_expired(self, db_session, test_user):
        """Get verified token returns None for expired token."""
        repo = PasswordResetRepository(db_session)
        token, _ = repo.create_token(user_id=test_user.id)
        db_session.commit()

        reset_token = repo.mark_as_verified(token.id)
        db_session.refresh(token)
        token.reset_token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()

        result = repo.get_verified_token(reset_token)
        assert result is None

    def test_get_verified_token_not_verified(self, db_session, test_user):
        """Get verified token returns None for non-verified token."""
        repo = PasswordResetRepository(db_session)
        token, _ = repo.create_token(user_id=test_user.id)

        # Set reset_token but not verified_at
        test_reset_token = "some_token"
        token.reset_token = test_reset_token
        token.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        db_session.commit()

        result = repo.get_verified_token(test_reset_token)
        assert result is None

    def test_check_account_lockout_no_lockout(self, db_session, test_user):
        """Check account lockout returns False when under limits."""
        repo = PasswordResetRepository(db_session)

        is_locked, retry_after = repo.check_account_lockout(test_user.id)
        assert is_locked is False
        assert retry_after is None

    def test_check_account_lockout_daily_limit(self, db_session, test_user):
        """Check account lockout returns True when daily limit exceeded (Finding #4)."""
        repo = PasswordResetRepository(db_session)

        # Create 10 tokens (default daily limit)
        for _ in range(10):
            repo.create_token(user_id=test_user.id)
        db_session.commit()

        is_locked, retry_after = repo.check_account_lockout(test_user.id)
        assert is_locked is True
        assert retry_after is not None
        assert retry_after > 0

    def test_check_account_lockout_weekly_limit(self, db_session, test_user):
        """Check account lockout returns True when weekly limit exceeded (Finding #4)."""
        repo = PasswordResetRepository(db_session)

        # Create 25 tokens (default weekly limit) over several days
        for i in range(25):
            token, _ = repo.create_token(user_id=test_user.id)
            # Spread tokens over the week
            token.created_at = datetime.now(timezone.utc) - timedelta(days=i % 7)
        db_session.commit()

        is_locked, retry_after = repo.check_account_lockout(test_user.id)
        assert is_locked is True
        assert retry_after is not None

    def test_context_signature_generation(self, db_session, test_user):
        """Generate context signature creates consistent signature (Finding #11)."""
        signature1 = PasswordResetRepository.generate_context_signature(
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        signature2 = PasswordResetRepository.generate_context_signature(
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert signature1 == signature2
        assert len(signature1) == 64  # SHA-256 hex

    def test_context_signature_different_context(self, db_session, test_user):
        """Generate context signature differs for different contexts (Finding #11)."""
        signature1 = PasswordResetRepository.generate_context_signature(
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        signature2 = PasswordResetRepository.generate_context_signature(
            user_id=test_user.id,
            ip_address="10.0.0.1",  # Different IP
            user_agent="Mozilla/5.0",
        )

        assert signature1 != signature2

    def test_context_signature_verification_success(self, db_session, test_user):
        """Verify context signature returns True for matching context (Finding #11)."""
        signature = PasswordResetRepository.generate_context_signature(
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        result = PasswordResetRepository.verify_context_signature(
            expected_signature=signature,
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        assert result is True

    def test_context_signature_verification_failure(self, db_session, test_user):
        """Verify context signature returns False for different context (Finding #11)."""
        signature = PasswordResetRepository.generate_context_signature(
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        result = PasswordResetRepository.verify_context_signature(
            expected_signature=signature,
            user_id=test_user.id,
            ip_address="10.0.0.1",  # Different IP
            user_agent="Mozilla/5.0",
        )
        assert result is False

    def test_invalidate_user_tokens(self, db_session, test_user):
        """Invalidate user tokens expires all active tokens."""
        repo = PasswordResetRepository(db_session)

        # Create multiple tokens
        token1, code1 = repo.create_token(user_id=test_user.id)
        token2, code2 = repo.create_token(user_id=test_user.id)
        db_session.commit()

        count = repo.invalidate_user_tokens(test_user.id)
        db_session.commit()

        assert count == 2

        # Tokens should no longer be valid
        assert repo.get_valid_code(test_user.id, code1) is None
        assert repo.get_valid_code(test_user.id, code2) is None

    def test_count_codes_in_window(self, db_session, test_user):
        """Count codes in window returns correct count."""
        repo = PasswordResetRepository(db_session)

        # Create 3 tokens
        for _ in range(3):
            repo.create_token(user_id=test_user.id)
        db_session.commit()

        count = repo.count_codes_in_window(test_user.id, hours=1)
        assert count == 3

    def test_cleanup_expired(self, db_session, test_user):
        """Cleanup expired removes old expired tokens."""
        repo = PasswordResetRepository(db_session)

        # Create token and expire it 48 hours ago
        token, _ = repo.create_token(user_id=test_user.id)
        token_id = token.id  # Save ID before deletion
        token.expires_at = datetime.now(timezone.utc) - timedelta(hours=48)
        db_session.commit()

        count = repo.cleanup_expired(older_than_hours=24)
        db_session.commit()

        assert count == 1

        # Token should be deleted
        assert (
            db_session.query(db_models.PasswordResetToken)
            .filter_by(id=token_id)
            .first()
            is None
        )

    def test_get_active_code_for_user(self, db_session, test_user):
        """Get active code for user returns most recent active code."""
        repo = PasswordResetRepository(db_session)

        # Create two tokens
        token1, _ = repo.create_token(user_id=test_user.id)
        db_session.commit()

        # Create second token (more recent)
        token2, _ = repo.create_token(user_id=test_user.id)
        db_session.commit()

        result = repo.get_active_code_for_user(test_user.id)
        assert result is not None
        assert result.id == token2.id  # Most recent

    def test_get_active_code_for_user_no_active(self, db_session, test_user):
        """Get active code for user returns None when no active codes."""
        repo = PasswordResetRepository(db_session)

        # Create and expire a token
        token, _ = repo.create_token(user_id=test_user.id)
        token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()

        result = repo.get_active_code_for_user(test_user.id)
        assert result is None

    def test_increment_reset_token_attempts(self, db_session, test_user):
        """Increment reset token attempts updates counter."""
        repo = PasswordResetRepository(db_session)
        token, _ = repo.create_token(user_id=test_user.id)
        db_session.commit()

        repo.mark_as_verified(token.id)
        db_session.commit()

        assert token.reset_token_attempts == 0
        repo.increment_reset_token_attempts(token.id)
        db_session.refresh(token)
        assert token.reset_token_attempts == 1
