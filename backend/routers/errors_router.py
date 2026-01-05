"""Frontend error reporting endpoint for admin notifications."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from authentication.auth import get_current_user_optional
from repositories.database import get_db
from repositories.db_models import User
from services.notification_service import NotificationService

router = APIRouter(prefix="/errors", tags=["errors"])


class FrontendErrorReport(BaseModel):
    """Frontend error report for admin notification."""

    error_type: str
    error_message: str
    url: str
    sentry_event_id: str | None = None


@router.post("/report", status_code=202)
async def report_frontend_error(
    error: FrontendErrorReport,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, str]:
    """
    Report a critical frontend error for admin notification.

    This endpoint is called by the frontend when a high-value error occurs,
    triggering an instant push notification to admins via ntfy.

    Returns 202 Accepted immediately (fire-and-forget notification).
    """
    # Build user info string
    user_info = (
        f"User: {current_user.display_name} ({current_user.email})"
        if current_user
        else "User: Anonymous"
    )

    # Build Sentry link if event ID provided
    sentry_link = ""
    if error.sentry_event_id:
        sentry_link = (
            f"\nSentry: https://sentry.io/issues/?query={error.sentry_event_id}"
        )

    # Truncate error message if too long
    error_msg = (
        error.error_message[:500]
        if len(error.error_message) > 500
        else error.error_message
    )

    # Send notification (fire-and-forget)
    NotificationService.notify_critical(
        title=f"Frontend Error: {error.error_type}",
        message=f"{error_msg}\n\nURL: {error.url}\n{user_info}{sentry_link}",
        click_url=error.url,
    )

    return {"status": "reported"}
