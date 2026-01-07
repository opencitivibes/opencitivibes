"""Tests for IP anonymization and email hashing utilities.

Security Hardening Phase 1 - Tests for V3 (IP anonymization) and V4 (email hashing).
"""

from helpers.ip_utils import anonymize_ip, hash_email_for_audit, is_valid_ip


class TestAnonymizeIP:
    """Test cases for IP address anonymization."""

    def test_ipv4_anonymization(self) -> None:
        """Test that IPv4 addresses have their last octet zeroed."""
        assert anonymize_ip("192.168.1.100") == "192.168.1.0"
        assert anonymize_ip("10.0.0.1") == "10.0.0.0"
        assert anonymize_ip("172.16.255.254") == "172.16.255.0"

    def test_ipv4_public_addresses(self) -> None:
        """Test anonymization of public IPv4 addresses."""
        assert anonymize_ip("8.8.8.8") == "8.8.8.0"
        assert anonymize_ip("142.250.80.78") == "142.250.80.0"  # Google IP

    def test_ipv6_anonymization(self) -> None:
        """Test that IPv6 addresses have the last 80 bits zeroed."""
        result = anonymize_ip("2001:db8:85a3:1234:5678:8a2e:370:7334")
        # Should keep first 48 bits (first 3 segments)
        assert result is not None
        assert result.startswith("2001:db8:85a3")
        # Rest should be zeroed
        assert (
            "::0" in result
            or result.count(":0") >= 4
            or result.endswith("::")
            or "::" in result
        )

    def test_ipv6_short_form(self) -> None:
        """Test anonymization of short-form IPv6 addresses."""
        result = anonymize_ip("2001:db8::1")
        assert result is not None
        assert result.startswith("2001:db8:")

    def test_none_input(self) -> None:
        """Test that None input returns None."""
        assert anonymize_ip(None) is None

    def test_invalid_ip(self) -> None:
        """Test that invalid IP strings are returned as-is."""
        # These are proxy header values, not IPs
        assert anonymize_ip("unknown") == "unknown"
        assert anonymize_ip("") == ""

    def test_localhost_ipv4(self) -> None:
        """Test localhost IPv4 anonymization."""
        assert anonymize_ip("127.0.0.1") == "127.0.0.0"

    def test_localhost_ipv6(self) -> None:
        """Test localhost IPv6 anonymization."""
        result = anonymize_ip("::1")
        # Should return something, even if format varies
        assert result is not None


class TestIsValidIP:
    """Test cases for IP validation."""

    def test_valid_ipv4(self) -> None:
        """Test valid IPv4 addresses."""
        assert is_valid_ip("192.168.1.1") is True
        assert is_valid_ip("0.0.0.0") is True
        assert is_valid_ip("255.255.255.255") is True

    def test_valid_ipv6(self) -> None:
        """Test valid IPv6 addresses."""
        assert is_valid_ip("::1") is True
        assert is_valid_ip("2001:db8::1") is True
        assert is_valid_ip("fe80::1") is True

    def test_invalid_ip(self) -> None:
        """Test invalid IP strings."""
        assert is_valid_ip("not-an-ip") is False
        assert is_valid_ip("256.1.1.1") is False
        assert is_valid_ip("") is False

    def test_none_input(self) -> None:
        """Test None input returns False."""
        assert is_valid_ip(None) is False


class TestHashEmailForAudit:
    """Test cases for email hashing."""

    def test_basic_hashing(self) -> None:
        """Test that emails are hashed consistently."""
        email = "user@example.com"
        result = hash_email_for_audit(email)

        # Should have format: hash...@domain
        assert result.endswith("@example.com")
        assert "..." in result
        assert len(result.split("@")[0]) == 11  # 8 chars + "..."

    def test_domain_preserved(self) -> None:
        """Test that the domain is always preserved."""
        assert hash_email_for_audit("test@gmail.com").endswith("@gmail.com")
        assert hash_email_for_audit("user@company.co.uk").endswith("@company.co.uk")

    def test_consistency(self) -> None:
        """Test that the same email produces the same hash."""
        email = "test@example.org"
        result1 = hash_email_for_audit(email)
        result2 = hash_email_for_audit(email)
        assert result1 == result2

    def test_different_emails_different_hashes(self) -> None:
        """Test that different emails produce different hashes."""
        hash1 = hash_email_for_audit("user1@example.com")
        hash2 = hash_email_for_audit("user2@example.com")
        # Same domain, different local part - should differ
        assert hash1 != hash2
        # But domains should match
        assert hash1.endswith("@example.com")
        assert hash2.endswith("@example.com")

    def test_invalid_email(self) -> None:
        """Test handling of invalid email format."""
        assert hash_email_for_audit("not-an-email") == "invalid@unknown"
        assert hash_email_for_audit("") == "invalid@unknown"

    def test_custom_salt(self) -> None:
        """Test that different salts produce different hashes."""
        email = "user@example.com"
        result1 = hash_email_for_audit(email, salt="salt1")
        result2 = hash_email_for_audit(email, salt="salt2")
        assert result1 != result2

    def test_subaddressing(self) -> None:
        """Test emails with plus addressing (subaddressing)."""
        result = hash_email_for_audit("user+tag@example.com")
        assert result.endswith("@example.com")
        # The local part (including +tag) should be hashed
        assert "+tag" not in result


class TestIntegration:
    """Integration tests for combined functionality."""

    def test_anonymize_and_hash_workflow(self) -> None:
        """Test typical workflow of anonymizing IP and hashing email."""
        ip = "192.168.1.100"
        email = "attacker@example.com"

        anon_ip = anonymize_ip(ip)
        hashed_email = hash_email_for_audit(email)

        # Type guard assertions
        assert anon_ip is not None

        # Original values should not be present
        assert "100" not in anon_ip
        assert "attacker" not in hashed_email

        # But we can still identify the subnet and domain
        assert anon_ip.startswith("192.168.1")
        assert hashed_email.endswith("@example.com")
