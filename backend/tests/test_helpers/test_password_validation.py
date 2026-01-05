"""Tests for password validation helper."""

from helpers.password_validation import (
    validate_password_complexity,
    get_password_strength_message,
    PasswordRequirements,
    DEFAULT_REQUIREMENTS,
)


class TestPasswordValidation:
    """Test cases for password complexity validation."""

    def test_valid_password_with_defaults(self):
        """Password meeting default requirements (strong) is valid."""
        # Default requirements: 12+ chars, uppercase, lowercase, digit, special
        is_valid, errors = validate_password_complexity("MyP@ssw0rd123!")
        assert is_valid is True
        assert len(errors) == 0

    def test_password_too_short(self):
        """Password shorter than minimum length fails."""
        # Use explicit weak requirements for this test
        weak_requirements = PasswordRequirements(
            min_length=8,
            require_uppercase=False,
            require_lowercase=True,
            require_digit=False,
            require_special=False,
        )
        is_valid, errors = validate_password_complexity("short", weak_requirements)
        assert is_valid is False
        assert len(errors) == 1
        assert "at least 8 characters" in errors[0]

    def test_missing_lowercase_when_required(self):
        """Password without lowercase fails when required."""
        requirements = PasswordRequirements(
            min_length=8, require_lowercase=True, require_uppercase=False
        )
        is_valid, errors = validate_password_complexity("PASSWORD123", requirements)
        assert is_valid is False
        assert "lowercase letter" in errors[0]

    def test_missing_uppercase_when_required(self):
        """Password without uppercase fails when required."""
        requirements = PasswordRequirements(
            min_length=8, require_uppercase=True, require_lowercase=False
        )
        is_valid, errors = validate_password_complexity("password123", requirements)
        assert is_valid is False
        assert "uppercase letter" in errors[0]

    def test_missing_digit_when_required(self):
        """Password without digit fails when required."""
        requirements = PasswordRequirements(
            min_length=8,
            require_digit=True,
            require_lowercase=False,
            require_uppercase=False,
            require_special=False,
        )
        is_valid, errors = validate_password_complexity("passwordabc", requirements)
        assert is_valid is False
        assert "digit" in errors[0]

    def test_missing_special_char_when_required(self):
        """Password without special character fails when required."""
        requirements = PasswordRequirements(
            min_length=8,
            require_special=True,
            require_lowercase=False,
            require_uppercase=False,
            require_digit=False,
        )
        is_valid, errors = validate_password_complexity("password123", requirements)
        assert is_valid is False
        assert "special character" in errors[0]

    def test_multiple_validation_errors(self):
        """Password can have multiple validation errors."""
        requirements = PasswordRequirements(
            min_length=10,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=True,
        )
        is_valid, errors = validate_password_complexity("short", requirements)
        assert is_valid is False
        assert len(errors) == 4  # too short, no uppercase, no digit, no special

    def test_complex_password_all_requirements(self):
        """Password meeting all complex requirements is valid."""
        requirements = PasswordRequirements(
            min_length=12,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=True,
        )
        is_valid, errors = validate_password_complexity("MyP@ssw0rd123!", requirements)
        assert is_valid is True
        assert len(errors) == 0

    def test_special_characters_in_password(self):
        """Password with various special characters is valid."""
        requirements = PasswordRequirements(
            min_length=8, require_special=True, require_lowercase=False
        )
        for special_char in "!@#$%^&*()_+-=[]{}|;:,.<>?":
            password = f"PASSWORD{special_char}123"
            is_valid, errors = validate_password_complexity(password, requirements)
            assert is_valid is True, f"Failed for special char: {special_char}"

    def test_default_requirements_instance(self):
        """DEFAULT_REQUIREMENTS has strong security values."""
        # Strong defaults for security (SEC-2030-002)
        assert DEFAULT_REQUIREMENTS.min_length == 12
        assert DEFAULT_REQUIREMENTS.require_lowercase is True
        assert DEFAULT_REQUIREMENTS.require_uppercase is True
        assert DEFAULT_REQUIREMENTS.require_digit is True
        assert DEFAULT_REQUIREMENTS.require_special is True


class TestPasswordStrengthMessage:
    """Test cases for password strength message generation."""

    def test_strength_message_strong_requirements(self):
        """Strength message for strong default requirements."""
        message = get_password_strength_message()
        assert "at least 12 characters" in message
        assert "one lowercase letter" in message
        assert "one uppercase letter" in message
        assert "one digit" in message
        assert "one special character" in message

    def test_strength_message_reads_default_requirements(self):
        """Strength message reflects DEFAULT_REQUIREMENTS."""
        # This test verifies the message is generated from DEFAULT_REQUIREMENTS
        message = get_password_strength_message()
        assert "Password must contain" in message or "Password must be" in message
        assert "12 characters" in message
