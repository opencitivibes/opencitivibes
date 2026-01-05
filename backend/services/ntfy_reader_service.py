"""
Service for reading notifications from ntfy cache.

Provides read-only access to ntfy notification history for admin panel display.
"""

import json
from datetime import datetime
from typing import TypedDict

import httpx
from loguru import logger

from models.config import settings
from models.notification_types import NotificationType


class NtfyMessage(TypedDict):
    """Parsed ntfy message structure."""

    id: str
    time: int  # Unix timestamp
    topic: str
    title: str
    message: str
    priority: int  # 1-5
    tags: list[str]
    click: str | None


class NotificationItem(TypedDict):
    """Notification item for frontend display."""

    id: str
    timestamp: str  # ISO 8601
    topic: str
    topic_display: str  # Human-readable topic name
    title: str
    message: str
    priority: str  # min, low, default, high, max
    priority_level: int  # 1-5 for sorting/styling
    tags: list[str]
    click_url: str | None


class NtfyReaderService:
    """
    Service for reading notification history from ntfy cache.

    All methods are class methods following project patterns.
    """

    # Map ntfy priority integers to strings
    PRIORITY_MAP: dict[int, str] = {
        1: "min",
        2: "low",
        3: "default",
        4: "high",
        5: "max",
    }

    # Human-readable topic names
    TOPIC_DISPLAY_MAP: dict[str, tuple[str, str]] = {
        "ideas": ("New Ideas", "Nouvelles idees"),
        "comments": ("Comments", "Commentaires"),
        "appeals": ("Appeals", "Appels"),
        "officials": ("Official Requests", "Demandes officielles"),
        "reports": ("Reports", "Signalements"),
        "critical": ("Critical", "Critique"),
    }

    @classmethod
    def _get_topic_display(cls, topic: str, language: str = "en") -> str:
        """Get human-readable topic name."""
        # Extract suffix from full topic name (e.g., "idees-admin-ideas" -> "ideas")
        prefix = settings.NTFY_TOPIC_PREFIX or "idees-admin"
        suffix = topic.replace(f"{prefix}-", "") if topic.startswith(prefix) else topic

        display = cls.TOPIC_DISPLAY_MAP.get(suffix)
        if display:
            return display[0] if language == "en" else display[1]
        return topic

    @classmethod
    def _get_all_topics(cls) -> list[str]:
        """Get list of all admin notification topics."""
        prefix = settings.NTFY_TOPIC_PREFIX or "idees-admin"
        return [f"{prefix}-{ntype.topic_suffix}" for ntype in NotificationType]

    @classmethod
    def _parse_message(cls, msg: dict, language: str = "en") -> NotificationItem:
        """Parse raw ntfy message into NotificationItem."""
        priority_int = msg.get("priority", 3)
        timestamp = datetime.fromtimestamp(msg.get("time", 0))

        return NotificationItem(
            id=msg.get("id", ""),
            timestamp=timestamp.isoformat(),
            topic=msg.get("topic", ""),
            topic_display=cls._get_topic_display(msg.get("topic", ""), language),
            title=msg.get("title", ""),
            message=msg.get("message", ""),
            priority=cls.PRIORITY_MAP.get(priority_int, "default"),
            priority_level=priority_int,
            tags=msg.get("tags", []),
            click_url=msg.get("click"),
        )

    @classmethod
    async def fetch_notifications(
        cls,
        since: str = "24h",
        limit: int = 50,
        language: str = "en",
    ) -> list[NotificationItem]:
        """
        Fetch recent notifications from all admin topics.

        Args:
            since: Time window (e.g., "24h", "1h", "30m")
            limit: Maximum notifications to return
            language: Language for topic display names ("en" or "fr")

        Returns:
            List of notifications sorted by timestamp (newest first)
        """
        ntfy_url = settings.NTFY_URL
        if not ntfy_url:
            logger.warning("NTFY_URL not configured, cannot fetch notifications")
            return []

        topics = cls._get_all_topics()
        all_notifications: list[NotificationItem] = []

        headers: dict[str, str] = {}
        if settings.NTFY_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {settings.NTFY_AUTH_TOKEN}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            for topic in topics:
                try:
                    # ntfy JSON poll endpoint
                    # poll=1 returns immediately with cached messages
                    # since=24h returns messages from last 24 hours
                    response = await client.get(
                        f"{ntfy_url}/{topic}/json",
                        params={"poll": "1", "since": since},
                        headers=headers,
                    )
                    response.raise_for_status()

                    # ntfy returns newline-delimited JSON
                    for line in response.text.strip().split("\n"):
                        if not line:
                            continue
                        try:
                            msg = json.loads(line)
                            # Skip keepalive messages
                            if msg.get("event") == "keepalive":
                                continue
                            # Only process message events
                            if msg.get("event", "message") == "message":
                                all_notifications.append(
                                    cls._parse_message(msg, language)
                                )
                        except json.JSONDecodeError:
                            logger.debug(
                                f"Skipping non-JSON line from ntfy: {line[:50]}"
                            )
                            continue

                except httpx.TimeoutException:
                    logger.warning(f"Timeout fetching notifications from {topic}")
                except httpx.HTTPStatusError as e:
                    logger.warning(
                        f"HTTP {e.response.status_code} fetching from {topic}"
                    )
                except Exception as e:
                    logger.warning(f"Error fetching from {topic}: {e}")

        # Sort by timestamp (newest first) and limit
        all_notifications.sort(key=lambda n: n["timestamp"], reverse=True)
        return all_notifications[:limit]

    @classmethod
    async def get_notification_counts(cls) -> dict[str, int]:
        """
        Get count of notifications per topic (last 24h).

        Returns:
            Dict mapping topic suffix to count
        """
        notifications = await cls.fetch_notifications(since="24h", limit=1000)

        counts: dict[str, int] = {}
        prefix = settings.NTFY_TOPIC_PREFIX or "idees-admin"

        for notif in notifications:
            topic = notif["topic"]
            suffix = (
                topic.replace(f"{prefix}-", "") if topic.startswith(prefix) else topic
            )
            counts[suffix] = counts.get(suffix, 0) + 1

        return counts
