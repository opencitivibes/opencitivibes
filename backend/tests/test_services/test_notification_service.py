"""Tests for NotificationService."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from models.notification_types import NotificationType
from services.notification_service import NotificationService


class TestNotificationType:
    """Test NotificationType enum."""

    def test_idea_pending_properties(self) -> None:
        """Test IDEA_PENDING notification type properties."""
        assert NotificationType.IDEA_PENDING.topic_suffix == "ideas"
        assert NotificationType.IDEA_PENDING.default_priority == "default"
        assert NotificationType.IDEA_PENDING.tags == "clipboard,new"

    def test_appeal_properties(self) -> None:
        """Test APPEAL notification type properties."""
        assert NotificationType.APPEAL.topic_suffix == "appeals"
        assert NotificationType.APPEAL.default_priority == "high"
        assert NotificationType.APPEAL.tags == "warning,appeal"

    def test_critical_properties(self) -> None:
        """Test CRITICAL notification type properties."""
        assert NotificationType.CRITICAL.topic_suffix == "critical"
        assert NotificationType.CRITICAL.default_priority == "max"
        assert NotificationType.CRITICAL.tags == "skull,warning"

    def test_all_types_have_valid_config(self) -> None:
        """All notification types should have valid configuration."""
        # ntfy supports: min, low, default, high, max, urgent (1-5)
        valid_priorities = {"min", "low", "default", "high", "max", "urgent"}
        for ntype in NotificationType:
            assert ntype.topic_suffix, f"{ntype.name} missing topic_suffix"
            assert (
                ntype.default_priority in valid_priorities
            ), f"{ntype.name} has invalid priority: {ntype.default_priority}"
            assert ntype.tags, f"{ntype.name} missing tags"

    def test_topic_suffixes_unique(self) -> None:
        """Topic suffixes should be unique across all types."""
        suffixes = [ntype.topic_suffix for ntype in NotificationType]
        assert len(suffixes) == len(set(suffixes)), "Duplicate topic suffixes found"

    def test_comment_pending_properties(self) -> None:
        """Test COMMENT_PENDING notification type properties."""
        assert NotificationType.COMMENT_PENDING.topic_suffix == "comments"
        assert NotificationType.COMMENT_PENDING.default_priority == "low"

    def test_official_request_properties(self) -> None:
        """Test OFFICIAL_REQUEST notification type properties."""
        assert NotificationType.OFFICIAL_REQUEST.topic_suffix == "officials"
        assert NotificationType.OFFICIAL_REQUEST.default_priority == "high"

    def test_report_properties(self) -> None:
        """Test REPORT notification type properties."""
        assert NotificationType.REPORT.topic_suffix == "reports"
        assert NotificationType.REPORT.default_priority == "urgent"


class TestNotificationService:
    """Test notification service functionality."""

    def test_get_topic(self) -> None:
        """Test topic name generation."""
        with patch("services.notification_service.settings") as mock_settings:
            mock_settings.NTFY_TOPIC_PREFIX = "myapp-admin"

            topic = NotificationService._get_topic(NotificationType.IDEA_PENDING)
            assert topic == "myapp-admin-ideas"

            topic = NotificationService._get_topic(NotificationType.APPEAL)
            assert topic == "myapp-admin-appeals"

    def test_get_topic_default_prefix(self) -> None:
        """Test topic uses default prefix when empty."""
        with patch("services.notification_service.settings") as mock_settings:
            mock_settings.NTFY_TOPIC_PREFIX = ""

            topic = NotificationService._get_topic(NotificationType.IDEA_PENDING)
            assert topic == "idees-admin-ideas"

    @pytest.mark.asyncio
    async def test_send_async_disabled_no_url(self) -> None:
        """Test that notifications are skipped when URL not configured."""
        with patch("services.notification_service.settings") as mock_settings:
            mock_settings.NTFY_URL = ""
            mock_settings.NTFY_ENABLED = True

            result = await NotificationService._send_async(
                NotificationType.IDEA_PENDING,
                "Test Title",
                "Test message",
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_send_async_disabled_flag(self) -> None:
        """Test that notifications are skipped when disabled."""
        with patch("services.notification_service.settings") as mock_settings:
            mock_settings.NTFY_URL = "http://ntfy:80"
            mock_settings.NTFY_ENABLED = False

            result = await NotificationService._send_async(
                NotificationType.IDEA_PENDING,
                "Test Title",
                "Test message",
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_send_async_success(self) -> None:
        """Test successful notification send."""
        with patch("services.notification_service.settings") as mock_settings:
            mock_settings.NTFY_URL = "http://ntfy:80"
            mock_settings.NTFY_ENABLED = True
            mock_settings.NTFY_TOPIC_PREFIX = "test"
            mock_settings.NTFY_AUTH_TOKEN = ""
            mock_settings.APP_URL = "http://localhost:3000"

            with patch("httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock()  # Sync method, not async
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                result = await NotificationService._send_async(
                    NotificationType.IDEA_PENDING,
                    "Test Title",
                    "Test message",
                    "http://example.com",
                )
                assert result is True

    @pytest.mark.asyncio
    async def test_send_async_with_auth_token(self) -> None:
        """Test notification send with auth token."""
        with patch("services.notification_service.settings") as mock_settings:
            mock_settings.NTFY_URL = "http://ntfy:80"
            mock_settings.NTFY_ENABLED = True
            mock_settings.NTFY_TOPIC_PREFIX = "test"
            mock_settings.NTFY_AUTH_TOKEN = "secret-token"
            mock_settings.APP_URL = "http://localhost:3000"

            with patch("httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.raise_for_status = Mock()  # Sync method, not async
                mock_post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value.post = mock_post

                result = await NotificationService._send_async(
                    NotificationType.IDEA_PENDING,
                    "Test Title",
                    "Test message",
                )
                assert result is True

                # Verify auth header was included
                call_kwargs = mock_post.call_args[1]
                assert "Authorization" in call_kwargs["headers"]
                assert call_kwargs["headers"]["Authorization"] == "Bearer secret-token"

    @pytest.mark.asyncio
    async def test_send_async_timeout(self) -> None:
        """Test handling of timeout."""
        with patch("services.notification_service.settings") as mock_settings:
            mock_settings.NTFY_URL = "http://ntfy:80"
            mock_settings.NTFY_ENABLED = True
            mock_settings.NTFY_TOPIC_PREFIX = "test"
            mock_settings.NTFY_AUTH_TOKEN = ""

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=httpx.TimeoutException("timeout")
                )

                result = await NotificationService._send_async(
                    NotificationType.IDEA_PENDING,
                    "Test Title",
                    "Test message",
                )
                assert result is False

    @pytest.mark.asyncio
    async def test_send_async_http_error(self) -> None:
        """Test handling of HTTP error."""
        with patch("services.notification_service.settings") as mock_settings:
            mock_settings.NTFY_URL = "http://ntfy:80"
            mock_settings.NTFY_ENABLED = True
            mock_settings.NTFY_TOPIC_PREFIX = "test"
            mock_settings.NTFY_AUTH_TOKEN = ""

            with patch("httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 500
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=httpx.HTTPStatusError(
                        "Internal Server Error",
                        request=AsyncMock(),
                        response=mock_response,
                    )
                )

                result = await NotificationService._send_async(
                    NotificationType.IDEA_PENDING,
                    "Test Title",
                    "Test message",
                )
                assert result is False

    @pytest.mark.asyncio
    async def test_send_async_general_exception(self) -> None:
        """Test handling of general exception."""
        with patch("services.notification_service.settings") as mock_settings:
            mock_settings.NTFY_URL = "http://ntfy:80"
            mock_settings.NTFY_ENABLED = True
            mock_settings.NTFY_TOPIC_PREFIX = "test"
            mock_settings.NTFY_AUTH_TOKEN = ""

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=Exception("Unexpected error")
                )

                result = await NotificationService._send_async(
                    NotificationType.IDEA_PENDING,
                    "Test Title",
                    "Test message",
                )
                assert result is False


class TestConvenienceMethods:
    """Test convenience notification methods."""

    def test_notify_new_idea(self) -> None:
        """Test notify_new_idea calls send_fire_and_forget correctly."""
        with patch.object(NotificationService, "send_fire_and_forget") as mock_send:
            with patch("services.notification_service.settings") as mock_settings:
                mock_settings.APP_URL = "http://test.com"

                NotificationService.notify_new_idea(
                    idea_id=123,
                    title="Test Idea",
                    category_name="Transport",
                    author_display_name="John Doe",
                )

                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert call_args[0][0] == NotificationType.IDEA_PENDING
                assert call_args[0][1] == "New Idea Pending Review"
                assert "Test Idea" in call_args[0][2]
                assert "Transport" in call_args[0][2]
                assert "John Doe" in call_args[0][2]
                assert "123" in call_args[0][2]

    def test_notify_new_comment(self) -> None:
        """Test notify_new_comment calls send_fire_and_forget correctly."""
        with patch.object(NotificationService, "send_fire_and_forget") as mock_send:
            with patch("services.notification_service.settings") as mock_settings:
                mock_settings.APP_URL = "http://test.com"

                NotificationService.notify_new_comment(
                    comment_id=456,
                    idea_title="Some Idea",
                    author_display_name="Jane Doe",
                )

                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert call_args[0][0] == NotificationType.COMMENT_PENDING
                assert call_args[0][1] == "Comment Awaiting Approval"

    def test_notify_appeal_truncates_reason(self) -> None:
        """Test notify_appeal truncates long reasons."""
        with patch.object(NotificationService, "send_fire_and_forget") as mock_send:
            with patch("services.notification_service.settings") as mock_settings:
                mock_settings.APP_URL = "http://test.com"

                long_reason = "A" * 300  # 300 characters

                NotificationService.notify_appeal(
                    idea_id=789,
                    idea_title="Rejected Idea",
                    appeal_reason=long_reason,
                    author_display_name="User",
                )

                mock_send.assert_called_once()
                call_args = mock_send.call_args
                message = call_args[0][2]
                # Should contain truncated reason (200 chars + "...")
                assert "A" * 200 + "..." in message

    def test_notify_report(self) -> None:
        """Test notify_report calls send_fire_and_forget correctly."""
        with patch.object(NotificationService, "send_fire_and_forget") as mock_send:
            with patch("services.notification_service.settings") as mock_settings:
                mock_settings.APP_URL = "http://test.com"

                NotificationService.notify_report(
                    content_type="idea",
                    content_id=111,
                    report_reason="Inappropriate content",
                    reporter_display_name="Reporter",
                )

                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert call_args[0][0] == NotificationType.REPORT
                assert "Content Reported: Idea" in call_args[0][1]

    def test_notify_official_request(self) -> None:
        """Test notify_official_request calls send_fire_and_forget correctly."""
        with patch.object(NotificationService, "send_fire_and_forget") as mock_send:
            with patch("services.notification_service.settings") as mock_settings:
                mock_settings.APP_URL = "http://test.com"

                NotificationService.notify_official_request(
                    user_id=999,
                    user_email="official@city.gov",
                    organization_name="City of Montreal",
                )

                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert call_args[0][0] == NotificationType.OFFICIAL_REQUEST
                assert call_args[0][1] == "Official Account Request"
                assert "official@city.gov" in call_args[0][2]
                assert "City of Montreal" in call_args[0][2]
                assert "999" in call_args[0][2]

    def test_notify_critical(self) -> None:
        """Test notify_critical uses max priority."""
        with patch.object(NotificationService, "send_fire_and_forget") as mock_send:
            with patch("services.notification_service.settings") as mock_settings:
                mock_settings.APP_URL = "http://test.com"

                NotificationService.notify_critical(
                    title="Security Alert",
                    message="Something bad happened",
                    click_url="http://test.com/admin",
                )

                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert call_args[0][0] == NotificationType.CRITICAL
                assert call_args[1]["priority_override"] == "max"


class TestFireAndForget:
    """Test fire-and-forget behavior."""

    @pytest.mark.asyncio
    async def test_send_fire_and_forget_with_event_loop(self) -> None:
        """Test fire-and-forget creates task when event loop exists."""
        with patch.object(NotificationService, "_send_async") as mock_send:
            mock_send.return_value = True

            NotificationService.send_fire_and_forget(
                NotificationType.IDEA_PENDING,
                "Test",
                "Message",
            )

            # Task was created (async context)
            # The task runs independently, so we just verify no exceptions

    def test_send_fire_and_forget_no_event_loop(self) -> None:
        """Test fire-and-forget fallback when no event loop running."""
        with patch.object(
            NotificationService, "_send_async", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = False

            # Call from sync context (no running event loop)
            NotificationService.send_fire_and_forget(
                NotificationType.IDEA_PENDING,
                "Test",
                "Message",
            )

            # Verify _send_async was called (via asyncio.run fallback)
            mock_send.assert_called_once_with(
                NotificationType.IDEA_PENDING,
                "Test",
                "Message",
                None,
                None,
            )
