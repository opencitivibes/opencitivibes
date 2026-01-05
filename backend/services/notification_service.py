"""
Admin notification service using self-hosted ntfy.

Sends push notifications to admin devices when content requires moderation.
Uses fire-and-forget pattern - failures are logged but don't block requests.
"""

import asyncio

import httpx
from loguru import logger

from models.config import settings
from models.notification_types import NotificationType


class NotificationService:
    """
    Unified admin notification service using self-hosted ntfy.

    All methods are fire-and-forget: they log failures but never raise
    exceptions or block the calling code.
    """

    @classmethod
    def _get_topic(cls, notification_type: NotificationType) -> str:
        """Build full topic name from type."""
        prefix = settings.NTFY_TOPIC_PREFIX or "idees-admin"
        return f"{prefix}-{notification_type.topic_suffix}"

    @classmethod
    async def _send_async(
        cls,
        notification_type: NotificationType,
        title: str,
        message: str,
        click_url: str | None = None,
        priority_override: str | None = None,
    ) -> bool:
        """
        Internal async send method.

        Args:
            notification_type: Determines topic and default priority
            title: Notification title (shown prominently)
            message: Notification body
            click_url: URL to open when notification is tapped
            priority_override: Override default priority (min/low/default/high/max)

        Returns:
            True if sent successfully, False otherwise
        """
        ntfy_url = settings.NTFY_URL
        if not ntfy_url or not settings.NTFY_ENABLED:
            logger.debug("Ntfy not configured or disabled, skipping notification")
            return False

        topic = cls._get_topic(notification_type)
        priority = priority_override or notification_type.default_priority

        headers: dict[str, str] = {
            "Title": title,
            "Priority": priority,
            "Tags": notification_type.tags,
        }

        # Add auth token if configured
        if settings.NTFY_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {settings.NTFY_AUTH_TOKEN}"

        # Add click action if URL provided
        if click_url:
            headers["Click"] = click_url
            headers["Actions"] = f"view, Open, {click_url}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{ntfy_url}/{topic}",
                    headers=headers,
                    content=message,
                )
                response.raise_for_status()
                logger.info(f"Notification sent to {topic}: {title}")
                return True
        except httpx.TimeoutException:
            logger.warning(f"Ntfy timeout sending to {topic}: {title}")
            return False
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"Ntfy HTTP error {e.response.status_code} for {topic}: {title}"
            )
            return False
        except Exception as e:
            logger.warning(f"Ntfy error sending to {topic}: {e}")
            return False

    @classmethod
    def send_fire_and_forget(
        cls,
        notification_type: NotificationType,
        title: str,
        message: str,
        click_url: str | None = None,
        priority_override: str | None = None,
    ) -> None:
        """
        Send notification without blocking (fire-and-forget).

        Creates a background task that will complete independently.
        Safe to call from sync or async context.

        Args:
            notification_type: Determines topic and default priority
            title: Notification title
            message: Notification body
            click_url: URL to open when tapped
            priority_override: Override default priority
        """
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create task
            loop.create_task(
                cls._send_async(
                    notification_type, title, message, click_url, priority_override
                )
            )
        except RuntimeError:
            # No running loop, run synchronously (shouldn't happen in FastAPI)
            logger.debug("No event loop, running notification sync")
            asyncio.run(
                cls._send_async(
                    notification_type, title, message, click_url, priority_override
                )
            )

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    @classmethod
    def notify_new_idea(
        cls,
        idea_id: int,
        title: str,
        category_name: str,
        author_display_name: str,
    ) -> None:
        """
        Notify admins of new idea pending review.

        Args:
            idea_id: Database ID of the idea
            title: Idea title
            category_name: Category display name
            author_display_name: Author's display name
        """
        cls.send_fire_and_forget(
            NotificationType.IDEA_PENDING,
            "New Idea Pending Review",
            f"{title}\n\nCategory: {category_name}\nAuthor: {author_display_name}\nID: {idea_id}",
            f"{settings.APP_URL}/admin/moderation?tab=ideas",
        )

    @classmethod
    def notify_new_comment(
        cls,
        comment_id: int,
        idea_title: str,
        author_display_name: str,
    ) -> None:
        """
        Notify admins of comment awaiting approval.

        Args:
            comment_id: Database ID of the comment
            idea_title: Title of the idea being commented on
            author_display_name: Comment author's display name
        """
        cls.send_fire_and_forget(
            NotificationType.COMMENT_PENDING,
            "Comment Awaiting Approval",
            f"On: {idea_title}\nAuthor: {author_display_name}\nID: {comment_id}",
            f"{settings.APP_URL}/admin/moderation?tab=comments",
        )

    @classmethod
    def notify_appeal(
        cls,
        idea_id: int,
        idea_title: str,
        appeal_reason: str,
        author_display_name: str,
    ) -> None:
        """
        Notify admins of user appeal for rejected idea.

        Args:
            idea_id: Database ID of the idea
            idea_title: Title of the rejected idea
            appeal_reason: User's reason for appeal
            author_display_name: User who submitted the appeal
        """
        # Truncate reason to avoid overly long notifications
        reason_preview = (
            appeal_reason[:200] + "..." if len(appeal_reason) > 200 else appeal_reason
        )
        cls.send_fire_and_forget(
            NotificationType.APPEAL,
            "Appeal Submitted",
            f"Idea: {idea_title}\nBy: {author_display_name}\n\nReason: {reason_preview}",
            f"{settings.APP_URL}/admin/moderation?tab=appeals&idea={idea_id}",
        )

    @classmethod
    def notify_official_request(
        cls,
        user_id: int,
        user_email: str,
        organization_name: str,
    ) -> None:
        """
        Notify admins of official account verification request.

        Args:
            user_id: Database ID of the user
            user_email: User's email
            organization_name: Claimed organization name
        """
        cls.send_fire_and_forget(
            NotificationType.OFFICIAL_REQUEST,
            "Official Account Request",
            f"User: {user_email}\nOrganization: {organization_name}\nID: {user_id}",
            f"{settings.APP_URL}/admin/users?filter=official-pending",
        )

    @classmethod
    def notify_report(
        cls,
        content_type: str,  # "idea" or "comment"
        content_id: int,
        report_reason: str,
        reporter_display_name: str,
    ) -> None:
        """
        Notify admins of reported content.

        Args:
            content_type: Type of content ("idea" or "comment")
            content_id: Database ID of the content
            report_reason: Reason for the report
            reporter_display_name: Display name of reporter
        """
        cls.send_fire_and_forget(
            NotificationType.REPORT,
            f"Content Reported: {content_type.title()}",
            f"Type: {content_type}\nID: {content_id}\nBy: {reporter_display_name}\n\nReason: {report_reason}",
            f"{settings.APP_URL}/admin/moderation?tab=reports",
        )

    @classmethod
    def notify_critical(
        cls,
        title: str,
        message: str,
        click_url: str | None = None,
    ) -> None:
        """
        Send critical/urgent notification (security, system issues).

        Args:
            title: Alert title
            message: Alert details
            click_url: Optional URL for more info
        """
        cls.send_fire_and_forget(
            NotificationType.CRITICAL,
            title,
            message,
            click_url or settings.APP_URL,
            priority_override="max",
        )
