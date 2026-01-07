"""
Time formatting utilities for the API.

Provides relative time formatting and timestamp standardization.
"""

from datetime import datetime, timezone


def format_relative_time(dt: datetime) -> str:
    """
    Format a datetime as a human-readable relative time string.

    Args:
        dt: The datetime to format (should be UTC)

    Returns:
        A human-readable string like "2 hours ago", "5 minutes ago", etc.
    """
    now = datetime.now(timezone.utc)

    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 0:
        return "just now"

    if seconds < 60:
        return "just now"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    days = hours // 24
    if days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"

    weeks = days // 7
    if weeks < 4:
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"

    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"

    years = days // 365
    return f"{years} year{'s' if years != 1 else ''} ago"


def format_iso8601(dt: datetime) -> str:
    """
    Format a datetime as ISO 8601 string.

    Args:
        dt: The datetime to format

    Returns:
        ISO 8601 formatted string (e.g., "2024-01-15T10:30:00Z")
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def mask_ip_address(ip: str | None) -> str | None:
    """
    Mask an IP address for privacy (show only first octet for IPv4).

    Args:
        ip: IP address string or None

    Returns:
        Masked IP like "192.x.x.x" for IPv4 or first segment for IPv6
    """
    if ip is None:
        return None

    if ":" in ip:
        # IPv6 - show first two segments
        parts = ip.split(":")
        if len(parts) >= 2:
            return f"{parts[0]}:{parts[1]}:*:*:*:*:*:*"
        return ip

    # IPv4 - show only first octet
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.x.x.x"

    return ip


def truncate_user_agent(ua: str | None, max_length: int = 80) -> str | None:
    """
    Truncate and format user agent for display.

    Extracts browser and OS info for a concise representation.

    Args:
        ua: Full user agent string or None
        max_length: Maximum length for the result

    Returns:
        Truncated user agent like "Chrome/120 (Windows)" or None
    """
    if ua is None:
        return None

    # Try to extract browser/version and OS
    ua_lower = ua.lower()

    browser = "Unknown"
    if "chrome" in ua_lower and "edg" not in ua_lower:
        browser = _extract_version(ua, "Chrome")
    elif "firefox" in ua_lower:
        browser = _extract_version(ua, "Firefox")
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser = _extract_version(ua, "Safari")
    elif "edg" in ua_lower:
        browser = _extract_version(ua, "Edg")

    os_name = "Unknown"
    if "windows" in ua_lower:
        os_name = "Windows"
    elif "mac" in ua_lower:
        os_name = "macOS"
    elif "linux" in ua_lower:
        os_name = "Linux"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"

    result = f"{browser} ({os_name})"
    if len(result) > max_length:
        return result[:max_length]
    return result


def _extract_version(ua: str, browser_name: str) -> str:
    """Extract browser name and major version from user agent."""
    import re

    pattern = rf"{browser_name}/(\d+)"
    match = re.search(pattern, ua, re.IGNORECASE)
    if match:
        return f"{browser_name}/{match.group(1)}"
    return browser_name
