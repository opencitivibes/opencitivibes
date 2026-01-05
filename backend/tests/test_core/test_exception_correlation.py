"""Tests for exception correlation ID behavior."""

import pytest

from core.correlation import set_correlation_id
from models.exceptions import (
    AuthenticationException,
    BusinessRuleException,
    DomainException,
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)


class TestDomainExceptionCorrelationId:
    """Tests for correlation ID in DomainException."""

    def setup_method(self) -> None:
        """Reset correlation context before each test."""
        set_correlation_id("")

    def test_uses_context_correlation_id(self) -> None:
        """Exception should use correlation ID from context if available."""
        context_id = "context1"
        set_correlation_id(context_id)

        exc = DomainException("Test error")
        assert exc.correlation_id == context_id

    def test_generates_id_when_no_context(self) -> None:
        """Exception should generate new ID if no context available."""
        set_correlation_id("")

        exc = DomainException("Test error")
        # Should be 8 hex characters
        assert len(exc.correlation_id) == 8
        assert all(c in "0123456789abcdef" for c in exc.correlation_id)

    def test_accepts_explicit_correlation_id(self) -> None:
        """Exception should use explicit correlation ID if provided."""
        explicit_id = "explicit"
        set_correlation_id("context_id")  # Set context to something else

        exc = DomainException("Test error", correlation_id=explicit_id)
        assert exc.correlation_id == explicit_id

    def test_explicit_overrides_context(self) -> None:
        """Explicit correlation ID should override context."""
        set_correlation_id("context_id")

        exc = DomainException("Test error", correlation_id="override")
        assert exc.correlation_id == "override"


class TestExceptionInheritance:
    """Tests that child exceptions inherit correlation ID behavior."""

    def setup_method(self) -> None:
        """Reset correlation context before each test."""
        set_correlation_id("")

    @pytest.mark.parametrize(
        "exception_class",
        [
            NotFoundException,
            PermissionDeniedException,
            ValidationException,
            AuthenticationException,
            BusinessRuleException,
        ],
    )
    def test_child_exceptions_use_context_id(
        self, exception_class: type[DomainException]
    ) -> None:
        """All child exceptions should use context correlation ID."""
        context_id = "inherited"
        set_correlation_id(context_id)

        exc = exception_class("Test error")
        assert exc.correlation_id == context_id

    @pytest.mark.parametrize(
        "exception_class",
        [
            NotFoundException,
            PermissionDeniedException,
            ValidationException,
            AuthenticationException,
            BusinessRuleException,
        ],
    )
    def test_child_exceptions_generate_id(
        self, exception_class: type[DomainException]
    ) -> None:
        """All child exceptions should generate ID when no context."""
        set_correlation_id("")

        exc = exception_class("Test error")
        assert len(exc.correlation_id) == 8

    def test_message_preserved(self) -> None:
        """Exception message should be preserved."""
        exc = NotFoundException("User not found")
        assert exc.message == "User not found"
        assert str(exc) == "User not found"


class TestCorrelationIdUniqueness:
    """Tests for correlation ID uniqueness in exceptions."""

    def setup_method(self) -> None:
        """Reset correlation context before each test."""
        set_correlation_id("")

    def test_multiple_exceptions_without_context_get_unique_ids(self) -> None:
        """Exceptions without context should get unique IDs."""
        exc1 = DomainException("Error 1")
        exc2 = DomainException("Error 2")
        # Each should have a unique ID
        assert exc1.correlation_id != exc2.correlation_id

    def test_multiple_exceptions_with_context_get_same_id(self) -> None:
        """Exceptions with context should share the same ID."""
        set_correlation_id("shared_id")

        exc1 = DomainException("Error 1")
        exc2 = DomainException("Error 2")
        # Both should have the context ID
        assert exc1.correlation_id == "shared_id"
        assert exc2.correlation_id == "shared_id"
