"""
Password complexity validation helper.

Provides password strength validation with configurable requirements.
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class PasswordRequirements:
    """Password complexity requirements configuration."""

    min_length: int = 12
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    special_characters: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"


# Default requirements with strong security settings
# These ensure passwords meet industry best practices for security
DEFAULT_REQUIREMENTS = PasswordRequirements()


def validate_password_complexity(
    password: str,
    requirements: PasswordRequirements = DEFAULT_REQUIREMENTS,
) -> tuple[bool, List[str]]:
    """
    Validate password against complexity requirements.

    Args:
        password: Password to validate
        requirements: Password requirements configuration

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors: List[str] = []

    # Check minimum length
    if len(password) < requirements.min_length:
        errors.append(
            f"Password must be at least {requirements.min_length} characters long"
        )

    # Check uppercase requirement
    if requirements.require_uppercase and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    # Check lowercase requirement
    if requirements.require_lowercase and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    # Check digit requirement
    if requirements.require_digit and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    # Check special character requirement
    if requirements.require_special:
        special_pattern = re.escape(requirements.special_characters)
        if not re.search(f"[{special_pattern}]", password):
            errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors


def get_password_strength_message() -> str:
    """
    Get a user-friendly message describing password requirements.

    Returns:
        String describing password requirements
    """
    req = DEFAULT_REQUIREMENTS
    parts = [f"at least {req.min_length} characters"]

    if req.require_uppercase:
        parts.append("one uppercase letter")
    if req.require_lowercase:
        parts.append("one lowercase letter")
    if req.require_digit:
        parts.append("one digit")
    if req.require_special:
        parts.append("one special character")

    if len(parts) == 1:
        return f"Password must be {parts[0]}"

    return f"Password must contain {', '.join(parts[:-1])}, and {parts[-1]}"
