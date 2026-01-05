"""
Sentry SDK configuration with privacy-compliant settings.

Implements:
- Environment-based initialization
- PII scrubbing for GDPR/Quebec Law 25 compliance
- Smart sampling for free tier quota management
- Loguru integration
"""

import os
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.loguru import LoguruIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.types import Event, Hint


def _before_send(event: Event, hint: Hint) -> Event | None:
    """
    Scrub PII before sending to Sentry.

    GDPR/Quebec Law 25 compliance:
    - Remove email addresses
    - Anonymize IP addresses
    - Keep only user_id for traceability

    Args:
        event: Sentry event.
        hint: Additional context about the event.

    Returns:
        Modified event with PII removed, or None to drop the event.
    """
    # Scrub user PII
    user = event.get("user")
    if user:
        # Keep only ID
        user.pop("email", None)
        user.pop("username", None)
        if "ip_address" in user:
            user["ip_address"] = "{{auto}}"  # Anonymized by Sentry

    # Scrub request data that might contain PII
    request = event.get("request")
    if request and isinstance(request, dict):
        # Remove cookies (may contain session data)
        request.pop("cookies", None)
        # Scrub authorization header
        headers = request.get("headers")
        if isinstance(headers, dict) and "Authorization" in headers:
            headers["Authorization"] = "[Filtered]"

    return event


def _before_send_transaction(event: Event, hint: Hint) -> Event | None:
    """
    Filter out noisy transactions and mark slow ones.

    Args:
        event: Sentry transaction event.
        hint: Additional context.

    Returns:
        Event to send, or None to drop it.
    """
    transaction_name = event.get("transaction", "")

    # Skip health checks
    if transaction_name in ["/health", "/api/health", "GET /health", "GET /api/health"]:
        return None

    # Mark slow transactions (> 1 second)
    # Timestamps can be floats or ISO strings
    start_timestamp = event.get("start_timestamp")
    end_timestamp = event.get("timestamp")
    if start_timestamp and end_timestamp:
        try:
            # Convert to float if they're timestamps
            start_ts = (
                float(start_timestamp)
                if isinstance(start_timestamp, (int, float))
                else 0
            )
            end_ts = (
                float(end_timestamp) if isinstance(end_timestamp, (int, float)) else 0
            )
            if start_ts and end_ts:
                duration_s = end_ts - start_ts
                if duration_s > 1.0:
                    event.setdefault("tags", {})["performance"] = "slow"
                elif duration_s > 0.5:
                    event.setdefault("tags", {})["performance"] = "moderate"
        except (ValueError, TypeError):
            pass  # Skip marking if timestamp conversion fails

    return event


def _traces_sampler(sampling_context: dict[str, Any]) -> float:
    """
    Dynamic sampling based on endpoint and context.

    Optimized for free tier (10K performance units/month).
    With <1K requests/day, 20% sampling = ~6K units/month.

    Args:
        sampling_context: Context about the request being sampled.

    Returns:
        Sample rate between 0.0 and 1.0.
    """
    # If parent was sampled, continue the trace
    if sampling_context.get("parent_sampled") is True:
        return 1.0

    # Get request path
    asgi_scope = sampling_context.get("asgi_scope", {})
    path = asgi_scope.get("path", "")

    # Never trace health checks
    if path in ["/health", "/api/health"]:
        return 0.0

    # Higher sampling for admin and auth (security-relevant)
    if path.startswith("/api/admin") or path.startswith("/api/auth"):
        return 0.5

    # Default sampling rate - 20% to stay within free tier limits
    return 0.2


def init_sentry() -> None:
    """
    Initialize Sentry SDK with FastAPI integration.

    Call this BEFORE creating the FastAPI app instance.
    Sentry is disabled if SENTRY_DSN environment variable is not set.
    """
    dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        # Sentry disabled if no DSN
        return

    environment = os.getenv("ENVIRONMENT", "development")
    release = os.getenv("SENTRY_RELEASE", "unknown")

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        # Privacy: Do NOT send PII automatically
        send_default_pii=False,
        # Integrations
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            LoguruIntegration(),
        ],
        # Sampling
        traces_sampler=_traces_sampler,
        # Error sampling: capture all errors (low volume)
        sample_rate=1.0,
        # PII scrubbing
        before_send=_before_send,
        before_send_transaction=_before_send_transaction,
        # Additional settings
        attach_stacktrace=True,
        max_breadcrumbs=50,
        # Ignore common non-issues
        ignore_errors=[
            KeyboardInterrupt,
            SystemExit,
        ],
    )
