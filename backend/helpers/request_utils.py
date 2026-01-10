"""
Request utilities for extracting client information.

Provides helpers to extract IP addresses and user agent strings from
HTTP requests, handling proxy headers correctly.

Also includes helpers for device token handling (2FA Remember Device).
"""

from typing import Optional

from fastapi import Request


def get_client_ip(request: Request) -> Optional[str]:
    """
    Extract the client's real IP address from the request.

    Handles common proxy headers in order of precedence:
    1. CF-Connecting-IP (Cloudflare)
    2. X-Real-IP (nginx)
    3. X-Forwarded-For (standard proxy header, first IP)
    4. Direct client.host

    Args:
        request: FastAPI request object

    Returns:
        Client IP address or None if not available
    """
    # Cloudflare
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    # nginx proxy
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Standard proxy header (comma-separated, first is client)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in the list is the original client
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip

    # Direct connection
    if request.client:
        return request.client.host

    return None


def get_user_agent(request: Request) -> Optional[str]:
    """
    Extract the user agent string from the request.

    Truncates to 500 characters to prevent database issues.

    Args:
        request: FastAPI request object

    Returns:
        User agent string or None if not present
    """
    user_agent = request.headers.get("User-Agent")
    if user_agent:
        # Truncate to prevent issues with very long user agents
        return user_agent[:500]
    return None


def get_request_metadata(request: Request) -> dict:
    """
    Extract common metadata from a request.

    Returns a dictionary containing IP address and user agent.
    Useful for security logging.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with 'ip_address' and 'user_agent' keys
    """
    return {
        "ip_address": get_client_ip(request),
        "user_agent": get_user_agent(request),
    }


# ============================================================================
# Device Token Helpers (2FA Remember Device)
# ============================================================================


def get_device_token_from_request(request: Request) -> Optional[str]:
    """
    Extract device token from request for 2FA bypass.

    Checks multiple sources in order of precedence:
    1. X-Device-Token header (mobile apps, API clients)
    2. device_token cookie (web browsers)

    Args:
        request: FastAPI request object

    Returns:
        Device token string or None if not found
    """
    # Check header first (mobile apps, API clients)
    header_token = request.headers.get("X-Device-Token")
    if header_token:
        return header_token.strip()

    # Check cookie (web browsers)
    cookie_token = request.cookies.get("device_token")
    if cookie_token:
        return cookie_token.strip()

    return None


def set_device_token_cookie(
    response: "Response",
    device_token: str,
    expires_at: "datetime",
    is_production: bool = True,
) -> None:
    """
    Set a secure httpOnly cookie for device token.

    Security settings:
    - httpOnly=True: Prevents XSS access to token
    - secure=True: HTTPS only (production)
    - SameSite=Strict: Prevents CSRF
    - path=/: Available for all paths

    Args:
        response: FastAPI response object
        device_token: The device token to store
        expires_at: When the cookie/trust expires
        is_production: Whether to enforce HTTPS-only
    """
    from datetime import datetime, timezone

    # Calculate max_age from expires_at
    now = datetime.now(timezone.utc)
    # Ensure expires_at is timezone-aware (assume UTC if naive)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    max_age = int((expires_at - now).total_seconds())

    if max_age <= 0:
        # Token already expired, don't set cookie
        return

    response.set_cookie(
        key="device_token",
        value=device_token,
        max_age=max_age,
        expires=expires_at.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        path="/",
        httponly=True,
        secure=is_production,
        samesite="strict",
    )


def clear_device_token_cookie(response: "Response") -> None:
    """
    Clear the device token cookie.

    Used when:
    - User explicitly revokes device trust
    - Device token is invalid/expired
    - User logs out

    Args:
        response: FastAPI response object
    """
    response.delete_cookie(
        key="device_token",
        path="/",
        httponly=True,
        samesite="strict",
    )


# Import types for type hints
from datetime import datetime  # noqa: E402
from fastapi import Response  # noqa: E402, F811
