"""Beta access verification router.

Server-side beta password verification to prevent client-side exposure.
Fixes CRITICAL vulnerability V1 from security audit.
"""

import hmac

from fastapi import APIRouter, Request, Response
from loguru import logger

import models.schemas as schemas
from helpers.rate_limiter import limiter
from models.config import settings
from models.exceptions import ValidationException

router = APIRouter(prefix="/beta", tags=["beta"])

# Cookie configuration for beta access
BETA_COOKIE_NAME = "beta_access"
BETA_COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds


@router.post("/verify", response_model=schemas.BetaVerifyResponse)
@limiter.limit("5/minute")
def verify_beta_password(
    request: Request,
    response: Response,
    body: schemas.BetaVerifyRequest,
) -> schemas.BetaVerifyResponse:
    """
    Verify beta password server-side.

    Sets an httpOnly cookie on success for persistent access.
    Rate limited to 5 attempts per minute per IP to prevent brute force.

    Args:
        request: FastAPI request (required for rate limiter)
        response: FastAPI response (for setting cookie)
        body: Request body with password

    Returns:
        Success response if password is correct

    Raises:
        ValidationException: If password is incorrect (generic error)
    """
    # Check if beta mode is enabled
    if not settings.BETA_MODE:
        # Beta mode disabled, allow access
        _set_beta_cookie(response)
        logger.info("Beta mode disabled, granting access")
        return schemas.BetaVerifyResponse(success=True)

    # Check if password is configured
    if not settings.BETA_PASSWORD:
        # No password configured, allow access
        _set_beta_cookie(response)
        logger.warning("BETA_PASSWORD not configured, granting access")
        return schemas.BetaVerifyResponse(success=True)

    # Verify password using constant-time comparison

    if hmac.compare_digest(body.password, settings.BETA_PASSWORD):
        _set_beta_cookie(response)
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"Beta access granted from IP: {client_ip}")
        return schemas.BetaVerifyResponse(success=True)

    # Password incorrect - return generic error to prevent enumeration
    client_ip = request.client.host if request.client else "unknown"
    logger.warning(f"Failed beta access attempt from IP: {client_ip}")
    raise ValidationException("Invalid access code")


@router.get("/status", response_model=schemas.BetaStatusResponse)
def get_beta_status(request: Request) -> schemas.BetaStatusResponse:
    """
    Check if beta access has been granted via cookie.

    Returns whether beta mode is enabled and whether the user has access.
    """
    has_access = request.cookies.get(BETA_COOKIE_NAME) == "true"

    return schemas.BetaStatusResponse(
        beta_mode_enabled=settings.BETA_MODE,
        has_access=has_access or not settings.BETA_MODE,
    )


def _set_beta_cookie(response: Response) -> None:
    """Set the beta access cookie with secure attributes."""
    response.set_cookie(
        key=BETA_COOKIE_NAME,
        value="true",
        max_age=BETA_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.ENVIRONMENT != "development",  # HTTPS only in prod
        samesite="strict",
    )
