"""
Correlation ID generation and context management.

Provides unique, short IDs for error tracking across FE/BE.
"""

import uuid
from contextvars import ContextVar

# Context variable for request-scoped correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def generate_correlation_id() -> str:
    """
    Generate a short, unique correlation ID.

    Format: 8 hex characters (e.g., "abc123de")
    - Short enough for users to report verbally
    - Unique enough for practical purposes (4 billion combinations)

    Returns:
        8-character hexadecimal string.
    """
    return uuid.uuid4().hex[:8]


def get_correlation_id() -> str:
    """
    Get current request's correlation ID.

    Returns:
        The correlation ID for the current request context, or empty string if not set.
    """
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """
    Set correlation ID for current request context.

    Args:
        correlation_id: The correlation ID to set for this request.
    """
    correlation_id_var.set(correlation_id)
