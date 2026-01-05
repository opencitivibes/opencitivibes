"""Tests for Sentry SDK configuration with privacy-compliant settings."""

import os
from typing import Any
from unittest.mock import patch

import pytest

from core.sentry_config import (
    _before_send,
    _before_send_transaction,
    _traces_sampler,
    init_sentry,
)


class TestBeforeSendPIIScrubbing:
    """Tests for PII scrubbing in _before_send."""

    def test_scrubs_email_from_user(self) -> None:
        """User email should be removed from events."""
        event: dict[str, Any] = {
            "user": {
                "id": "123",
                "email": "user@example.com",
                "username": "testuser",
            }
        }
        result = _before_send(event, {})  # type: ignore[arg-type]
        assert result is not None
        assert "email" not in result.get("user", {})

    def test_scrubs_username_from_user(self) -> None:
        """Username should be removed from events."""
        event: dict[str, Any] = {
            "user": {
                "id": "123",
                "username": "testuser",
            }
        }
        result = _before_send(event, {})  # type: ignore[arg-type]
        assert result is not None
        assert "username" not in result.get("user", {})

    def test_anonymizes_ip_address(self) -> None:
        """IP address should be anonymized."""
        event: dict[str, Any] = {
            "user": {
                "id": "123",
                "ip_address": "192.168.1.100",
            }
        }
        result = _before_send(event, {})  # type: ignore[arg-type]
        assert result is not None
        assert result["user"]["ip_address"] == "{{auto}}"  # type: ignore[typeddict-item]

    def test_preserves_user_id(self) -> None:
        """User ID should be preserved for traceability."""
        event: dict[str, Any] = {
            "user": {
                "id": "123",
                "email": "user@example.com",
            }
        }
        result = _before_send(event, {})  # type: ignore[arg-type]
        assert result is not None
        assert result["user"]["id"] == "123"  # type: ignore[typeddict-item]

    def test_removes_cookies_from_request(self) -> None:
        """Cookies should be removed from request data."""
        event: dict[str, Any] = {
            "request": {
                "url": "/api/test",
                "cookies": {"session": "secret_session_value"},
            }
        }
        result = _before_send(event, {})  # type: ignore[arg-type]
        assert result is not None
        assert "cookies" not in result.get("request", {})

    def test_filters_authorization_header(self) -> None:
        """Authorization header should be filtered."""
        event: dict[str, Any] = {
            "request": {
                "url": "/api/test",
                "headers": {
                    "Authorization": "Bearer secret_token_123",
                    "Content-Type": "application/json",
                },
            }
        }
        result = _before_send(event, {})  # type: ignore[arg-type]
        assert result is not None
        assert result["request"]["headers"]["Authorization"] == "[Filtered]"  # type: ignore[typeddict-item, index]
        # Other headers should be preserved
        assert result["request"]["headers"]["Content-Type"] == "application/json"  # type: ignore[typeddict-item, index]

    def test_handles_event_without_user(self) -> None:
        """Should handle events without user data gracefully."""
        event: dict[str, Any] = {"message": "Test error"}
        result = _before_send(event, {})  # type: ignore[arg-type]
        assert result is not None
        assert result["message"] == "Test error"  # type: ignore[typeddict-item]

    def test_handles_event_without_request(self) -> None:
        """Should handle events without request data gracefully."""
        event: dict[str, Any] = {"message": "Test error", "user": {"id": "123"}}
        result = _before_send(event, {})  # type: ignore[arg-type]
        assert result is not None


class TestBeforeSendTransaction:
    """Tests for transaction filtering."""

    @pytest.mark.parametrize(
        "path",
        ["/health", "/api/health", "GET /health", "GET /api/health"],
    )
    def test_filters_health_check_paths(self, path: str) -> None:
        """Health check transactions should be filtered out."""
        event: dict[str, Any] = {"transaction": path}
        result = _before_send_transaction(event, {})  # type: ignore[arg-type]
        assert result is None

    def test_allows_non_health_check_paths(self) -> None:
        """Non-health-check transactions should pass through."""
        event: dict[str, Any] = {"transaction": "/api/ideas"}
        result = _before_send_transaction(event, {})  # type: ignore[arg-type]
        assert result is not None
        assert result["transaction"] == "/api/ideas"  # type: ignore[typeddict-item]


class TestTracesSampler:
    """Tests for dynamic trace sampling."""

    def test_never_samples_health_checks(self) -> None:
        """Health check endpoints should never be sampled."""
        context: dict[str, Any] = {"asgi_scope": {"path": "/health"}}
        assert _traces_sampler(context) == 0.0

        context = {"asgi_scope": {"path": "/api/health"}}
        assert _traces_sampler(context) == 0.0

    def test_higher_sampling_for_admin(self) -> None:
        """Admin endpoints should have 50% sampling."""
        context: dict[str, Any] = {"asgi_scope": {"path": "/api/admin/users"}}
        assert _traces_sampler(context) == 0.5

    def test_higher_sampling_for_auth(self) -> None:
        """Auth endpoints should have 50% sampling."""
        context: dict[str, Any] = {"asgi_scope": {"path": "/api/auth/login"}}
        assert _traces_sampler(context) == 0.5

    def test_default_sampling_rate(self) -> None:
        """Default sampling rate should be 20%."""
        context: dict[str, Any] = {"asgi_scope": {"path": "/api/ideas"}}
        assert _traces_sampler(context) == 0.2

    def test_respects_parent_sampling(self) -> None:
        """Should always sample if parent was sampled."""
        context: dict[str, Any] = {
            "parent_sampled": True,
            "asgi_scope": {"path": "/api/ideas"},
        }
        assert _traces_sampler(context) == 1.0

    def test_handles_missing_asgi_scope(self) -> None:
        """Should handle missing ASGI scope gracefully."""
        context: dict[str, Any] = {}
        # Default rate when path can't be determined
        assert _traces_sampler(context) == 0.2


class TestInitSentry:
    """Tests for Sentry initialization."""

    def test_init_sentry_without_dsn_does_nothing(self) -> None:
        """Sentry should not initialize without DSN."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing SENTRY_DSN
            os.environ.pop("SENTRY_DSN", None)
            # Should not raise any errors
            init_sentry()

    def test_init_sentry_with_dsn_initializes(self) -> None:
        """Sentry should initialize with valid DSN."""
        test_dsn = "https://test@o0.ingest.sentry.io/0"
        with patch("sentry_sdk.init") as mock_init:
            with patch.dict(os.environ, {"SENTRY_DSN": test_dsn}):
                init_sentry()
                mock_init.assert_called_once()

    def test_init_sentry_uses_environment_variables(self) -> None:
        """Sentry should use environment variables for configuration."""
        env_vars = {
            "SENTRY_DSN": "https://test@o0.ingest.sentry.io/0",
            "ENVIRONMENT": "production",
            "SENTRY_RELEASE": "1.2.3",
        }
        with patch("sentry_sdk.init") as mock_init:
            with patch.dict(os.environ, env_vars):
                init_sentry()
                call_kwargs = mock_init.call_args.kwargs
                assert call_kwargs["dsn"] == env_vars["SENTRY_DSN"]
                assert call_kwargs["environment"] == "production"
                assert call_kwargs["release"] == "1.2.3"

    def test_init_sentry_defaults(self) -> None:
        """Sentry should use defaults when env vars not set."""
        with patch("sentry_sdk.init") as mock_init:
            with patch.dict(
                os.environ, {"SENTRY_DSN": "https://test@o0.ingest.sentry.io/0"}
            ):
                # Clear optional vars
                os.environ.pop("ENVIRONMENT", None)
                os.environ.pop("SENTRY_RELEASE", None)
                init_sentry()
                call_kwargs = mock_init.call_args.kwargs
                assert call_kwargs["environment"] == "development"
                assert call_kwargs["release"] == "unknown"
