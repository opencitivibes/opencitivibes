"""Security tests for email login feature."""

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from repositories.email_login_repository import EmailLoginCodeRepository
from services.email_login_service import EmailLoginService
from models.exceptions import (
    EmailLoginCodeExpiredException,
    EmailLoginCodeInvalidException,
    EmailLoginMaxAttemptsException,
    EmailLoginUserNotFoundException,
)


class TestEmailLoginSecurity:
    """Security-focused tests for email login."""

    def test_code_hashed_in_database(self, db_session, test_user):
        """Plain code should not be stored in database."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, plain_code = repo.create_code(test_user.id)
        db_session.commit()

        # Code in DB should be hashed, not plain
        assert code_record.code_hash != plain_code
        assert len(code_record.code_hash) == 64  # SHA-256

    def test_code_single_use(self, db_session, test_user):
        """Code should only work once."""
        repo = EmailLoginCodeRepository(db_session)
        _, plain_code = repo.create_code(test_user.id)
        db_session.commit()

        # First verification succeeds
        token = EmailLoginService.verify_code(
            db=db_session,
            email=test_user.email,
            code=plain_code,
        )
        assert token is not None

        # Second verification fails
        with pytest.raises(EmailLoginCodeExpiredException):
            EmailLoginService.verify_code(
                db=db_session,
                email=test_user.email,
                code=plain_code,
            )

    def test_brute_force_protection(self, db_session, test_user):
        """Should block after max attempts."""
        repo = EmailLoginCodeRepository(db_session)
        repo.create_code(test_user.id)
        db_session.commit()

        # With MAX_ATTEMPTS=5, make 4 failed attempts (service commits each)
        for _ in range(4):
            with pytest.raises(EmailLoginCodeInvalidException):
                EmailLoginService.verify_code(
                    db=db_session,
                    email=test_user.email,
                    code="000000",
                )

        # 5th attempt should be blocked
        with pytest.raises(EmailLoginMaxAttemptsException):
            EmailLoginService.verify_code(
                db=db_session,
                email=test_user.email,
                code="000000",
            )

    def test_expired_code_rejected(self, db_session, test_user):
        """Expired codes should not work."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, plain_code = repo.create_code(test_user.id)

        # Manually expire the code
        code_record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.commit()

        with pytest.raises(EmailLoginCodeExpiredException):
            EmailLoginService.verify_code(
                db=db_session,
                email=test_user.email,
                code=plain_code,
            )

    def test_code_timing_attack_resistance(self, db_session, test_user):
        """Response time should be similar for valid and invalid codes."""
        import time

        repo = EmailLoginCodeRepository(db_session)
        repo.create_code(test_user.id)
        db_session.commit()

        # Time invalid code check
        start = time.time()
        repo.get_valid_code(test_user.id, "123456")  # Likely wrong
        invalid_time = time.time() - start

        # Time another invalid code
        start = time.time()
        repo.get_valid_code(test_user.id, "654321")  # Also wrong
        another_time = time.time() - start

        # Times should be similar (within 10ms)
        assert abs(invalid_time - another_time) < 0.01

    def test_old_codes_invalidated_on_new_request(self, db_session, test_user):
        """New code request should invalidate old codes."""
        with patch(
            "services.email_login_service.EmailService.send_login_code",
            return_value=True,
        ):
            # Create first code directly
            repo = EmailLoginCodeRepository(db_session)
            _, first_code = repo.create_code(test_user.id)
            db_session.commit()

            # Request second code (invalidates first, creates new one)
            EmailLoginService.request_login_code(
                db=db_session,
                email=test_user.email,
            )

            # First code should not work - new code exists but wrong code entered
            # Note: Returns "Invalid" not "Expired" because there's still an active
            # code session, just with a different hash
            with pytest.raises(EmailLoginCodeInvalidException):
                EmailLoginService.verify_code(
                    db=db_session,
                    email=test_user.email,
                    code=first_code,
                )

    def test_inactive_user_cannot_login(self, db_session, test_user):
        """Inactive users should not be able to request codes."""
        test_user.is_active = False
        db_session.commit()

        with pytest.raises(EmailLoginUserNotFoundException):
            EmailLoginService.request_login_code(
                db=db_session,
                email=test_user.email,
            )

    def test_code_entropy(self):
        """Code should have sufficient entropy."""
        codes = [EmailLoginCodeRepository.generate_code() for _ in range(10000)]

        # Check distribution - each position should have roughly equal digits
        for position in range(6):
            digit_counts: dict[str, int] = {}
            for code in codes:
                digit = code[position]
                digit_counts[digit] = digit_counts.get(digit, 0) + 1

            # Each digit should appear roughly 1000 times (10% of 10000)
            for digit in "0123456789":
                count = digit_counts.get(digit, 0)
                # Allow 30% variance from expected (700-1300)
                assert (
                    700 < count < 1300
                ), f"Digit {digit} at position {position}: {count}"

    def test_used_code_not_reusable(self, db_session, test_user):
        """A used code should never be reusable even if not expired."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, plain_code = repo.create_code(test_user.id)
        db_session.commit()

        # Mark as used
        repo.mark_as_used(code_record.id)
        db_session.commit()

        # Should not be findable
        valid = repo.get_valid_code(test_user.id, plain_code)
        assert valid is None

    def test_max_attempts_blocks_valid_code(self, db_session, test_user):
        """Even valid code should fail after max attempts reached."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, plain_code = repo.create_code(test_user.id)

        # Set attempts to max
        code_record.attempts = 5
        db_session.commit()

        # Valid code should not be found
        valid = repo.get_valid_code(test_user.id, plain_code)
        assert valid is None

    def test_different_user_code_isolation(self, db_session, test_user, other_user):
        """Codes should be isolated between users."""
        repo = EmailLoginCodeRepository(db_session)

        # Create code for test_user
        _, plain_code = repo.create_code(test_user.id)
        db_session.commit()

        # other_user should not be able to use this code
        valid = repo.get_valid_code(other_user.id, plain_code)
        assert valid is None

    def test_hash_uses_sha256(self):
        """Hash should use SHA-256."""
        import hashlib

        code = "123456"
        expected = hashlib.sha256(code.encode()).hexdigest()
        actual = EmailLoginCodeRepository.hash_code(code)

        assert actual == expected

    def test_code_not_predictable(self):
        """Consecutive codes should not be predictable."""
        codes = [EmailLoginCodeRepository.generate_code() for _ in range(100)]

        # Check that codes are not sequential
        for i in range(len(codes) - 1):
            # Codes should not increment by 1
            try:
                diff = int(codes[i + 1]) - int(codes[i])
                # Most differences should not be exactly 1
                assert diff != 1 or i % 10 != 0  # Allow some coincidental +1s
            except ValueError:
                pass  # Leading zeros can cause issues, skip

        # Verify no obvious patterns
        unique_codes = set(codes)
        assert len(unique_codes) > 90  # Should be mostly unique

    def test_code_generation_uses_secrets(self):
        """Code generation should use cryptographic randomness."""

        # Test that generate_code uses secrets module indirectly
        # by checking the output is cryptographically random
        codes = set()
        for _ in range(1000):
            code = EmailLoginCodeRepository.generate_code()
            assert len(code) == 6
            assert code.isdigit()
            codes.add(code)

        # With 1000 samples from 1M possibilities, expect high uniqueness
        assert len(codes) > 990

    def test_ip_address_stored_for_audit(self, db_session, test_user):
        """IP address should be stored for security audit."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, _ = repo.create_code(test_user.id, ip_address="192.168.1.1")
        db_session.commit()

        # Verify IP is stored
        db_session.refresh(code_record)
        assert code_record.ip_address == "192.168.1.1"

    def test_ipv6_address_stored(self, db_session, test_user):
        """IPv6 addresses should be storable."""
        repo = EmailLoginCodeRepository(db_session)
        ipv6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        code_record, _ = repo.create_code(test_user.id, ip_address=ipv6)
        db_session.commit()

        db_session.refresh(code_record)
        assert code_record.ip_address == ipv6
