"""Models package - Pydantic schemas and domain types."""

from .notification_types import NotificationConfig, NotificationType

__all__ = [
    "NotificationConfig",
    "NotificationType",
]
