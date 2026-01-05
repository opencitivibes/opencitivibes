"""
Admin notifications router.

Provides read-only access to ntfy notification history for admin panel.
Also provides diagnostic endpoints for testing notification systems.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from authentication.auth import get_admin_user
from models.notification_types import NotificationType
import repositories.db_models as db_models
from repositories.database import get_db
from services.notification_service import NotificationService
from services.ntfy_reader_service import NotificationItem, NtfyReaderService

router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


@router.get("", response_model=list[NotificationItem])
async def get_notifications(
    since: str = Query(default="24h", pattern=r"^\d+[hmsd]$"),
    limit: int = Query(default=50, ge=1, le=200),
    language: str = Query(default="en", pattern=r"^(en|fr)$"),
    _current_user: db_models.User = Depends(get_admin_user),
    _db: Session = Depends(get_db),
) -> list[NotificationItem]:
    """
    Get recent admin notifications from ntfy cache.

    Args:
        since: Time window (e.g., "24h", "1h", "30m", "7d")
        limit: Maximum notifications to return (1-200)
        language: Language for display names ("en" or "fr")

    Returns:
        List of notifications sorted by timestamp (newest first)

    Requires: Global admin access
    """
    return await NtfyReaderService.fetch_notifications(
        since=since,
        limit=limit,
        language=language,
    )


@router.get("/counts", response_model=dict[str, int])
async def get_notification_counts(
    _current_user: db_models.User = Depends(get_admin_user),
    _db: Session = Depends(get_db),
) -> dict[str, int]:
    """
    Get count of notifications per topic (last 24h).

    Returns:
        Dict mapping topic name to count (e.g., {"ideas": 5, "comments": 3})

    Requires: Global admin access
    """
    return await NtfyReaderService.get_notification_counts()


class TestNotificationResponse(BaseModel):
    """Response for test notification endpoint."""

    success: bool
    message: str


@router.post("/test", response_model=TestNotificationResponse)
async def send_test_notification(
    current_user: db_models.User = Depends(get_admin_user),
    _db: Session = Depends(get_db),
) -> TestNotificationResponse:
    """
    Send a test notification to verify ntfy is working.

    Sends a test notification to the admin-ideas topic with low priority.

    Returns:
        Success status and message

    Requires: Global admin access
    """
    success = await NotificationService._send_async(
        notification_type=NotificationType.IDEA_PENDING,
        title="Test Notification",
        message=f"Diagnostics test from {current_user.email}",
        priority_override="low",
    )

    if success:
        return TestNotificationResponse(
            success=True,
            message="Test notification sent successfully",
        )
    return TestNotificationResponse(
        success=False,
        message="Failed to send notification - check ntfy configuration",
    )


class SmtpTestResponse(BaseModel):
    """Response for SMTP test endpoint."""

    success: bool
    provider: str
    host: str | None
    port: int | None
    message: str
    details: str | None = None


@router.post("/test-smtp", response_model=SmtpTestResponse)
async def test_smtp_connection(
    _current_user: db_models.User = Depends(get_admin_user),
    _db: Session = Depends(get_db),
) -> SmtpTestResponse:
    """
    Test SMTP server connectivity.

    Tests connection to the configured SMTP server without sending an email.
    Useful for diagnosing email login issues.

    Returns:
        Success status, provider info, and connection details

    Requires: Global admin access
    """
    import smtplib
    import socket

    from models.config import settings

    provider = settings.EMAIL_PROVIDER.lower()

    # Console provider is always "successful" but emails aren't sent
    if provider == "console":
        return SmtpTestResponse(
            success=True,
            provider="console (dev mode)",
            host=None,
            port=None,
            message="Emails printed to backend logs, not sent",
            details="Set EMAIL_PROVIDER=smtp for real delivery",
        )

    # SendGrid doesn't use SMTP
    if provider == "sendgrid":
        api_key_set = bool(settings.SENDGRID_API_KEY)
        return SmtpTestResponse(
            success=api_key_set,
            provider="sendgrid",
            host=None,
            port=None,
            message="SendGrid API key configured"
            if api_key_set
            else "SendGrid API key not set",
            details=None,
        )

    # Test SMTP connection
    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    use_tls = settings.SMTP_USE_TLS
    use_ssl = settings.SMTP_USE_SSL

    try:
        # Connect with timeout - choose connection type based on SSL/TLS settings
        if use_ssl:
            # Implicit SSL (port 465) - connection is encrypted from start
            server = smtplib.SMTP_SSL(host, port, timeout=10)
            security_mode = "SSL"
        elif use_tls:
            # STARTTLS (port 587) - upgrade to TLS after connection
            server = smtplib.SMTP(host, port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
            security_mode = "STARTTLS"
        else:
            # Plain SMTP (not recommended)
            server = smtplib.SMTP(host, port, timeout=10)
            server.ehlo()
            security_mode = "none"

        # Check if auth is configured
        auth_configured = bool(settings.SMTP_USER and settings.SMTP_PASSWORD)
        if auth_configured:
            try:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                auth_status = "authenticated"
            except smtplib.SMTPAuthenticationError:
                server.quit()
                return SmtpTestResponse(
                    success=False,
                    provider="smtp",
                    host=host,
                    port=port,
                    message="SMTP authentication failed",
                    details="Check SMTP_USER and SMTP_PASSWORD",
                )
        else:
            auth_status = "no auth required"

        server.quit()

        return SmtpTestResponse(
            success=True,
            provider="smtp",
            host=host,
            port=port,
            message=f"SMTP connection successful ({auth_status})",
            details=f"Security: {security_mode}",
        )

    except socket.timeout:
        return SmtpTestResponse(
            success=False,
            provider="smtp",
            host=host,
            port=port,
            message="Connection timeout",
            details="SMTP server not responding within 10 seconds",
        )
    except ConnectionRefusedError:
        return SmtpTestResponse(
            success=False,
            provider="smtp",
            host=host,
            port=port,
            message="Connection refused",
            details="SMTP server not accepting connections",
        )
    except smtplib.SMTPException as e:
        return SmtpTestResponse(
            success=False,
            provider="smtp",
            host=host,
            port=port,
            message="SMTP error",
            details=str(e),
        )
    except OSError as e:
        return SmtpTestResponse(
            success=False,
            provider="smtp",
            host=host,
            port=port,
            message="Network error",
            details=str(e),
        )
