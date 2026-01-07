"""
IP address and email utilities for privacy compliance.

Provides IP anonymization (Law 25 compliance) and email hashing
to prevent user enumeration through failed login logs.
"""

import hashlib
import ipaddress
from typing import Optional


def anonymize_ip(ip: Optional[str]) -> Optional[str]:
    """
    Anonymize an IP address for privacy-compliant storage.

    For IPv4: Zeros the last octet (e.g., 192.168.1.100 -> 192.168.1.0)
    For IPv6: Zeros the last 80 bits (e.g., 2001:db8::1 -> 2001:db8:0:0:0:0:0:0)

    This provides sufficient anonymization for Law 25 compliance while
    preserving enough information for pattern detection (subnet analysis).

    Args:
        ip: IP address string or None

    Returns:
        Anonymized IP address or None if input is None
    """
    if ip is None:
        return None

    try:
        addr = ipaddress.ip_address(ip)

        if isinstance(addr, ipaddress.IPv4Address):
            # Zero the last octet for IPv4
            octets = str(addr).split(".")
            octets[3] = "0"
            return ".".join(octets)

        elif isinstance(addr, ipaddress.IPv6Address):
            # Zero the last 80 bits for IPv6 (keep first 48 bits)
            # This is more aggressive anonymization for IPv6
            network = ipaddress.IPv6Network(f"{addr}/48", strict=False)
            return str(network.network_address)

    except ValueError:
        # Invalid IP address - return as-is (might be a proxy header value)
        return ip

    # Unreachable, but makes type checker happy
    return None  # pragma: no cover


def is_valid_ip(ip: Optional[str]) -> bool:
    """
    Validate an IP address string.

    Args:
        ip: IP address string to validate

    Returns:
        True if valid IPv4 or IPv6 address, False otherwise
    """
    if ip is None:
        return False

    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def hash_email_for_audit(email: str, salt: str = "security_audit") -> str:
    """
    Hash an email address for security audit logging.

    Preserves the domain for pattern analysis while hashing the local part.
    Format: first 8 chars of hash + @domain.tld

    This prevents user enumeration through failed login logs while
    still allowing analysis of attack patterns by domain.

    Args:
        email: Email address to hash
        salt: Salt for hashing (use consistent salt for matching)

    Returns:
        Hashed email in format "a3f2c1d4...@example.com"
    """
    if not email or "@" not in email:
        return "invalid@unknown"

    local_part, domain = email.rsplit("@", 1)

    # Hash the local part with salt
    hash_input = f"{salt}:{local_part}".encode("utf-8")
    hash_value = hashlib.sha256(hash_input).hexdigest()

    # Return first 8 chars of hash + domain
    return f"{hash_value[:8]}...@{domain}"
