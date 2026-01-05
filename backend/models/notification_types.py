"""Notification type definitions for admin alerts."""

from enum import Enum
from typing import NamedTuple


class NotificationConfig(NamedTuple):
    """Configuration for a notification type."""

    topic_suffix: str
    default_priority: str  # min, low, default, high, max
    tags: str  # comma-separated emoji shortcodes


class NotificationType(Enum):
    """
    Notification types with their topic suffix, default priority, and tags.

    Each type maps to a specific ntfy topic for routing.
    Admins can subscribe to specific topics based on their role.
    """

    IDEA_PENDING = NotificationConfig("ideas", "default", "clipboard,new")
    COMMENT_PENDING = NotificationConfig("comments", "low", "speech_balloon")
    APPEAL = NotificationConfig("appeals", "high", "warning,appeal")
    OFFICIAL_REQUEST = NotificationConfig("officials", "high", "office,verified")
    REPORT = NotificationConfig("reports", "urgent", "rotating_light,report")
    CRITICAL = NotificationConfig("critical", "max", "skull,warning")

    @property
    def topic_suffix(self) -> str:
        """Get the topic suffix for this notification type."""
        return self.value.topic_suffix

    @property
    def default_priority(self) -> str:
        """Get the default priority for this notification type."""
        return self.value.default_priority

    @property
    def tags(self) -> str:
        """Get the tags for this notification type."""
        return self.value.tags
