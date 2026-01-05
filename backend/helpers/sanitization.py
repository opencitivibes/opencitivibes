"""
HTML sanitization utilities to prevent XSS attacks.

This module provides functions to sanitize user input before storage,
removing potentially malicious HTML/JavaScript while preserving safe formatting.
"""

from typing import Optional

import bleach

# Conservative list of allowed HTML tags for rich text
ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "ul",
    "ol",
    "li",
    "blockquote",
]

# No attributes allowed by default (prevents event handlers)
ALLOWED_ATTRIBUTES: dict[str, list[str]] = {}


def sanitize_html(content: Optional[str]) -> Optional[str]:
    """
    Sanitize HTML content to prevent XSS attacks.

    Removes all HTML tags except those in ALLOWED_TAGS whitelist.
    Strips all attributes including event handlers (onclick, onerror, etc.).

    Args:
        content: Raw HTML content from user input

    Returns:
        Sanitized HTML with only allowed tags, or None if input is None

    Examples:
        >>> sanitize_html('<script>alert("XSS")</script>Safe')
        'Safe'
        >>> sanitize_html('<p>Hello <b>world</b></p>')
        '<p>Hello <b>world</b></p>'
        >>> sanitize_html('<img src=x onerror=alert(1)>')
        ''
    """
    if content is None:
        return None

    return bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )


def sanitize_plain_text(content: Optional[str]) -> Optional[str]:
    """
    Strip all HTML tags for plain text fields.

    Use this for fields that should never contain HTML, like titles.

    Args:
        content: Raw content from user input

    Returns:
        Plain text with all HTML removed, or None if input is None

    Examples:
        >>> sanitize_plain_text('<script>alert(1)</script>Title')
        'Title'
        >>> sanitize_plain_text('<b>Bold</b> text')
        'Bold text'
    """
    if content is None:
        return None

    return bleach.clean(content, tags=[], strip=True)


def sanitize_url(url: Optional[str]) -> Optional[str]:
    """
    Sanitize URLs to prevent javascript: protocol attacks.

    Only allows http, https, and mailto protocols.

    Args:
        url: URL from user input

    Returns:
        Sanitized URL or empty string if protocol is not allowed

    Examples:
        >>> sanitize_url('javascript:alert(1)')
        ''
        >>> sanitize_url('https://example.com')
        'https://example.com'
    """
    if url is None:
        return None

    url = url.strip()
    allowed_protocols = ("http://", "https://", "mailto:")

    if url.lower().startswith("javascript:"):
        return ""

    if url and not url.startswith(allowed_protocols):
        # Relative URLs are allowed
        if url.startswith("/") or ":" not in url.split("/")[0]:
            return url
        return ""

    return url
