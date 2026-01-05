"""Tests for EmailLoginCodeRepository."""

from datetime import datetime, timedelta, timezone

from repositories.email_login_repository import EmailLoginCodeRepository


class TestEmailLoginCodeRepository:
    """Test suite for EmailLoginCodeRepository."""

    def test_generate_code_length(self):
        """Generated code should be 6 digits."""
        code = EmailLoginCodeRepository.generate_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_is_random(self):
        """Generated codes should be different."""
        codes = {EmailLoginCodeRepository.generate_code() for _ in range(100)}
        # Very unlikely to have fewer than 90 unique codes in 100 generations
        assert len(codes) > 90

    def test_hash_code_consistent(self):
        """Same code should produce same hash."""
        code = "123456"
        hash1 = EmailLoginCodeRepository.hash_code(code)
        hash2 = EmailLoginCodeRepository.hash_code(code)
        assert hash1 == hash2

    def test_hash_code_length(self):
        """Hash should be 64 characters (SHA-256 hex)."""
        hash_val = EmailLoginCodeRepository.hash_code("123456")
        assert len(hash_val) == 64

    def test_hash_code_different_for_different_codes(self):
        """Different codes should have different hashes."""
        hash1 = EmailLoginCodeRepository.hash_code("123456")
        hash2 = EmailLoginCodeRepository.hash_code("654321")
        assert hash1 != hash2

    def test_create_code_returns_model_and_plain_code(self, db_session, test_user):
        """create_code should return both model and plain text code."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, plain_code = repo.create_code(test_user.id)

        assert code_record is not None
        assert code_record.user_id == test_user.id
        assert code_record.used_at is None
        assert code_record.attempts == 0
        assert len(plain_code) == 6
        assert code_record.code_hash == repo.hash_code(plain_code)

    def test_create_code_sets_expiration(self, db_session, test_user):
        """Code should have future expiration time."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, _ = repo.create_code(test_user.id)

        now = datetime.now(timezone.utc)
        assert code_record.expires_at > now
        # Should expire in ~10 minutes (default)
        assert code_record.expires_at < now + timedelta(minutes=15)

    def test_create_code_stores_ip_address(self, db_session, test_user):
        """IP address should be stored with code."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, _ = repo.create_code(test_user.id, ip_address="192.168.1.1")

        assert code_record.ip_address == "192.168.1.1"

    def test_get_valid_code_success(self, db_session, test_user):
        """Valid code should be found."""
        repo = EmailLoginCodeRepository(db_session)
        _, plain_code = repo.create_code(test_user.id)
        db_session.commit()

        found = repo.get_valid_code(test_user.id, plain_code)
        assert found is not None

    def test_get_valid_code_wrong_code(self, db_session, test_user):
        """Wrong code should not be found."""
        repo = EmailLoginCodeRepository(db_session)
        repo.create_code(test_user.id)
        db_session.commit()

        found = repo.get_valid_code(test_user.id, "000000")
        assert found is None

    def test_get_valid_code_expired(self, db_session, test_user):
        """Expired code should not be found."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, plain_code = repo.create_code(test_user.id)
        # Manually expire the code
        code_record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.commit()

        found = repo.get_valid_code(test_user.id, plain_code)
        assert found is None

    def test_get_valid_code_already_used(self, db_session, test_user):
        """Used code should not be found."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, plain_code = repo.create_code(test_user.id)
        code_record.used_at = datetime.now(timezone.utc)
        db_session.commit()

        found = repo.get_valid_code(test_user.id, plain_code)
        assert found is None

    def test_get_valid_code_max_attempts(self, db_session, test_user):
        """Code with max attempts should not be found."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, plain_code = repo.create_code(test_user.id)
        code_record.attempts = 5  # Max attempts
        db_session.commit()

        found = repo.get_valid_code(test_user.id, plain_code)
        assert found is None

    def test_increment_attempts(self, db_session, test_user):
        """Attempts should increment."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, _ = repo.create_code(test_user.id)
        db_session.commit()

        assert code_record.attempts == 0
        repo.increment_attempts(code_record.id)
        db_session.refresh(code_record)
        assert code_record.attempts == 1

    def test_mark_as_used(self, db_session, test_user):
        """used_at should be set."""
        repo = EmailLoginCodeRepository(db_session)
        code_record, _ = repo.create_code(test_user.id)
        db_session.commit()

        assert code_record.used_at is None
        repo.mark_as_used(code_record.id)
        db_session.refresh(code_record)
        assert code_record.used_at is not None

    def test_invalidate_user_codes(self, db_session, test_user):
        """Old codes should be invalidated."""
        repo = EmailLoginCodeRepository(db_session)

        # Create multiple codes
        for _ in range(3):
            repo.create_code(test_user.id)
        db_session.commit()

        # Invalidate all
        count = repo.invalidate_user_codes(test_user.id)
        assert count == 3

        # Check no active codes remain
        active = repo.get_active_code_for_user(test_user.id)
        assert active is None

    def test_count_codes_in_window(self, db_session, test_user):
        """Should count codes created in time window."""
        repo = EmailLoginCodeRepository(db_session)

        # Create 3 codes
        for _ in range(3):
            repo.create_code(test_user.id)
        db_session.commit()

        count = repo.count_codes_in_window(test_user.id, hours=1)
        assert count == 3

    def test_get_active_code_for_user(self, db_session, test_user):
        """Should find most recent active code."""
        repo = EmailLoginCodeRepository(db_session)
        _, plain_code = repo.create_code(test_user.id)
        db_session.commit()

        active = repo.get_active_code_for_user(test_user.id)
        assert active is not None
        assert active.code_hash == repo.hash_code(plain_code)

    def test_get_active_code_for_user_no_code(self, db_session, test_user):
        """Should return None when no active code."""
        repo = EmailLoginCodeRepository(db_session)

        active = repo.get_active_code_for_user(test_user.id)
        assert active is None

    def test_cleanup_expired(self, db_session, test_user):
        """Should delete old expired codes."""
        repo = EmailLoginCodeRepository(db_session)

        # Create a code and expire it
        code_record, _ = repo.create_code(test_user.id)
        code_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=25)
        db_session.commit()

        # Cleanup should delete it
        count = repo.cleanup_expired(older_than_hours=24)
        assert count == 1
