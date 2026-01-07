"""Tests for request_utils helper functions."""

from unittest.mock import MagicMock


from helpers.request_utils import get_client_ip, get_request_metadata, get_user_agent


class TestGetClientIp:
    """Test cases for get_client_ip function."""

    def test_cloudflare_header(self):
        """Test extraction from CF-Connecting-IP header."""
        request = MagicMock()
        request.headers = {"CF-Connecting-IP": "203.0.113.50"}
        request.client = MagicMock(host="10.0.0.1")

        ip = get_client_ip(request)

        assert ip == "203.0.113.50"

    def test_cloudflare_header_with_whitespace(self):
        """Test that whitespace is stripped from CF header."""
        request = MagicMock()
        request.headers = {"CF-Connecting-IP": "  203.0.113.50  "}
        request.client = MagicMock(host="10.0.0.1")

        ip = get_client_ip(request)

        assert ip == "203.0.113.50"

    def test_x_real_ip_header(self):
        """Test extraction from X-Real-IP header (nginx)."""
        request = MagicMock()
        request.headers = {"X-Real-IP": "192.168.1.100"}
        request.client = MagicMock(host="10.0.0.1")

        ip = get_client_ip(request)

        assert ip == "192.168.1.100"

    def test_x_forwarded_for_single(self):
        """Test extraction from X-Forwarded-For with single IP."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "172.16.0.50"}
        request.client = MagicMock(host="10.0.0.1")

        ip = get_client_ip(request)

        assert ip == "172.16.0.50"

    def test_x_forwarded_for_multiple(self):
        """Test extraction from X-Forwarded-For with multiple IPs."""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "203.0.113.50, 70.41.3.18, 150.172.238.178"
        }
        request.client = MagicMock(host="10.0.0.1")

        ip = get_client_ip(request)

        # Should return first IP (original client)
        assert ip == "203.0.113.50"

    def test_direct_connection(self):
        """Test extraction from direct connection."""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="192.168.1.1")

        ip = get_client_ip(request)

        assert ip == "192.168.1.1"

    def test_no_client(self):
        """Test handling when client is None."""
        request = MagicMock()
        request.headers = {}
        request.client = None

        ip = get_client_ip(request)

        assert ip is None

    def test_ipv6_address(self):
        """Test handling of IPv6 addresses."""
        request = MagicMock()
        request.headers = {"CF-Connecting-IP": "2001:db8:85a3::8a2e:370:7334"}
        request.client = None

        ip = get_client_ip(request)

        assert ip == "2001:db8:85a3::8a2e:370:7334"

    def test_header_precedence(self):
        """Test that headers are checked in correct order."""
        request = MagicMock()
        request.headers = {
            "CF-Connecting-IP": "203.0.113.1",  # Should win
            "X-Real-IP": "203.0.113.2",
            "X-Forwarded-For": "203.0.113.3, 10.0.0.1",
        }
        request.client = MagicMock(host="10.0.0.1")

        ip = get_client_ip(request)

        assert ip == "203.0.113.1"  # Cloudflare takes precedence


class TestGetUserAgent:
    """Test cases for get_user_agent function."""

    def test_normal_user_agent(self):
        """Test extraction of normal user agent."""
        request = MagicMock()
        request.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        ua = get_user_agent(request)

        assert ua == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

    def test_no_user_agent(self):
        """Test handling when User-Agent is missing."""
        request = MagicMock()
        request.headers = {}

        ua = get_user_agent(request)

        assert ua is None

    def test_truncation(self):
        """Test that very long user agents are truncated."""
        request = MagicMock()
        long_ua = "x" * 1000
        request.headers = {"User-Agent": long_ua}

        ua = get_user_agent(request)

        assert ua is not None
        assert len(ua) == 500
        assert ua == "x" * 500


class TestGetRequestMetadata:
    """Test cases for get_request_metadata function."""

    def test_returns_both_values(self):
        """Test that function returns both IP and user agent."""
        request = MagicMock()
        request.headers = {
            "CF-Connecting-IP": "192.168.1.1",
            "User-Agent": "Test Browser",
        }
        request.client = None

        metadata = get_request_metadata(request)

        assert metadata["ip_address"] == "192.168.1.1"
        assert metadata["user_agent"] == "Test Browser"

    def test_handles_missing_values(self):
        """Test that function handles missing values gracefully."""
        request = MagicMock()
        request.headers = {}
        request.client = None

        metadata = get_request_metadata(request)

        assert metadata["ip_address"] is None
        assert metadata["user_agent"] is None
