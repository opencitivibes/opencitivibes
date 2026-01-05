"""Router for email login (magic link/passwordless) authentication."""

from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from helpers.rate_limiter import limiter
from models.schemas import (
    EmailLoginRequest,
    EmailLoginResponse,
    EmailLoginStatusResponse,
    EmailLoginVerify,
    Token,
)
from repositories.database import get_db
from services.email_login_service import EmailLoginService

router = APIRouter(prefix="/auth/email-login", tags=["auth", "email-login"])


def _get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request, considering proxies."""
    # Check X-Forwarded-For header (from reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client
    if request.client:
        return request.client.host

    return None


def _get_language(request: Request) -> str:
    """Extract preferred language from Accept-Language header."""
    accept_lang = request.headers.get("Accept-Language", "en")
    # Simple parsing - check if French is preferred
    if accept_lang.lower().startswith("fr"):
        return "fr"
    return "en"


@router.post("/request", response_model=EmailLoginResponse)
@limiter.limit("10/minute")  # Per IP
def request_login_code(
    request: Request,
    data: EmailLoginRequest,
    db: Session = Depends(get_db),
) -> EmailLoginResponse:
    """
    Request a login code to be sent to the user's email.

    Rate limited to:
    - 3 requests per email per hour (enforced at service level)
    - 10 requests per IP per minute

    The code will be valid for 10 minutes (configurable).
    """
    ip_address = _get_client_ip(request)
    language = _get_language(request)

    expires_in = EmailLoginService.request_login_code(
        db=db,
        email=data.email,
        ip_address=ip_address,
        language=language,
    )

    return EmailLoginResponse(
        message="Login code sent to your email",
        expires_in_seconds=expires_in,
    )


@router.post("/verify", response_model=Token)
@limiter.limit("10/minute")  # Per IP
def verify_login_code(
    request: Request,
    data: EmailLoginVerify,
    db: Session = Depends(get_db),
) -> Token:
    """
    Verify a login code and receive an access token.

    Rate limited to 10 attempts per IP per minute.

    On success, returns the same token format as regular login.
    """
    ip_address = _get_client_ip(request)

    return EmailLoginService.verify_code(
        db=db,
        email=data.email,
        code=data.code,
        ip_address=ip_address,
    )


@router.get("/status", response_model=EmailLoginStatusResponse)
@limiter.limit("20/minute")
def check_code_status(
    request: Request,
    email: str,
    db: Session = Depends(get_db),
) -> EmailLoginStatusResponse:
    """
    Check if there's a pending code for an email.

    Useful for showing "resend" timer on frontend.

    Returns:
        - has_pending_code: bool
        - expires_in_seconds: int (if pending code exists)
    """
    remaining = EmailLoginService.check_pending_code(db, email)

    if remaining is not None and remaining > 0:
        return EmailLoginStatusResponse(
            has_pending_code=True,
            expires_in_seconds=remaining,
        )

    return EmailLoginStatusResponse(
        has_pending_code=False,
        expires_in_seconds=0,
    )
