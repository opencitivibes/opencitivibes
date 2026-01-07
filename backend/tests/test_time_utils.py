"""
Tests for time utility functions.

Tests relative time formatting, IP masking, and user agent truncation.
"""

from datetime import datetime, timedelta, timezone

from helpers.time_utils import (
    format_iso8601,
    format_relative_time,
    mask_ip_address,
    truncate_user_agent,
)


class TestFormatRelativeTime:
    """Tests for format_relative_time function."""

    def test_just_now(self):
        """Times within last minute show 'just now'."""
        now = datetime.now(timezone.utc)
        result = format_relative_time(now)
        assert result == "just now"

    def test_minutes_ago(self):
        """Times in minutes range."""
        five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = format_relative_time(five_min_ago)
        assert "5 minutes ago" == result

    def test_minute_singular(self):
        """Singular minute."""
        one_min_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
        result = format_relative_time(one_min_ago)
        assert result == "1 minute ago"

    def test_hours_ago(self):
        """Times in hours range."""
        two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
        result = format_relative_time(two_hours_ago)
        assert "2 hours ago" == result

    def test_hour_singular(self):
        """Singular hour."""
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        result = format_relative_time(one_hour_ago)
        assert result == "1 hour ago"

    def test_days_ago(self):
        """Times in days range."""
        three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
        result = format_relative_time(three_days_ago)
        assert "3 days ago" == result

    def test_weeks_ago(self):
        """Times in weeks range."""
        two_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=2)
        result = format_relative_time(two_weeks_ago)
        assert "2 weeks ago" == result

    def test_months_ago(self):
        """Times in months range."""
        two_months_ago = datetime.now(timezone.utc) - timedelta(days=60)
        result = format_relative_time(two_months_ago)
        assert "2 months ago" == result

    def test_years_ago(self):
        """Times in years range."""
        two_years_ago = datetime.now(timezone.utc) - timedelta(days=730)
        result = format_relative_time(two_years_ago)
        assert "2 years ago" == result

    def test_naive_datetime(self):
        """Handles naive datetime (assumes UTC)."""
        naive_time = datetime.now() - timedelta(hours=2)
        result = format_relative_time(naive_time)
        assert "hour" in result


class TestFormatIso8601:
    """Tests for format_iso8601 function."""

    def test_formats_correctly(self):
        """Formats datetime as ISO 8601."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = format_iso8601(dt)
        assert result == "2024-01-15T10:30:00Z"

    def test_handles_naive_datetime(self):
        """Handles naive datetime (assumes UTC)."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = format_iso8601(dt)
        assert result == "2024-01-15T10:30:00Z"


class TestMaskIpAddress:
    """Tests for mask_ip_address function."""

    def test_ipv4_masking(self):
        """IPv4 addresses are masked correctly."""
        result = mask_ip_address("192.168.1.100")
        assert result == "192.x.x.x"

    def test_ipv6_masking(self):
        """IPv6 addresses show first two segments."""
        result = mask_ip_address("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert result == "2001:0db8:*:*:*:*:*:*"

    def test_handles_none(self):
        """Returns None for None input."""
        result = mask_ip_address(None)
        assert result is None

    def test_localhost(self):
        """Handles localhost correctly."""
        result = mask_ip_address("127.0.0.1")
        assert result == "127.x.x.x"


class TestTruncateUserAgent:
    """Tests for truncate_user_agent function."""

    def test_chrome_windows(self):
        """Extracts Chrome on Windows."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
        result = truncate_user_agent(ua)
        assert "Chrome/120" in result
        assert "Windows" in result

    def test_firefox_mac(self):
        """Extracts Firefox on macOS."""
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
        result = truncate_user_agent(ua)
        assert "Firefox/121" in result
        assert "macOS" in result

    def test_safari_ios(self):
        """Extracts Safari on iOS."""
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1) AppleWebKit/605.1.15 Safari/605.1.15"
        result = truncate_user_agent(ua)
        assert "Safari" in result
        assert "iOS" in result

    def test_handles_none(self):
        """Returns None for None input."""
        result = truncate_user_agent(None)
        assert result is None

    def test_max_length(self):
        """Respects max length."""
        ua = "A" * 200
        result = truncate_user_agent(ua, max_length=50)
        assert len(result) <= 50 if result else True
