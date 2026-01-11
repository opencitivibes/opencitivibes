"""Password reset router endpoints."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

import models.schemas as schemas
from helpers.rate_limiter import limiter
from helpers.request_utils import get_client_ip, get_user_agent
from repositories.database import get_db
from services.password_reset_service import PasswordResetService

router = APIRouter(prefix="/auth/password-reset", tags=["password-reset"])


@router.post("/request", response_model=schemas.PasswordResetRequestResponse)
@limiter.limit("5/minute")
def request_password_reset(
    request: Request,
    body: schemas.PasswordResetRequest,
    db: Session = Depends(get_db),
) -> schemas.PasswordResetRequestResponse:
    """
    Request a password reset code.

    Rate limited to 5 per minute.

    Returns the same response whether the email exists or not to prevent
    user enumeration attacks.
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    language = request.headers.get("Accept-Language", "en")[:2]

    result = PasswordResetService.request_reset(
        db=db,
        email=body.email,
        ip_address=ip_address,
        user_agent=user_agent,
        language=language,
    )

    return schemas.PasswordResetRequestResponse(
        message=result["message"],
        expires_in_seconds=result["expires_in_seconds"],
    )


@router.post("/verify", response_model=schemas.PasswordResetVerifyResponse)
@limiter.limit("10/minute")
def verify_reset_code(
    request: Request,
    body: schemas.PasswordResetVerify,
    db: Session = Depends(get_db),
) -> schemas.PasswordResetVerifyResponse:
    """
    Verify a password reset code.

    Rate limited to 10 per minute.

    Errors:
    - 400: Invalid code
    - 410: Code expired or max attempts exceeded
    - 429: Rate limit exceeded
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    result = PasswordResetService.verify_code(
        db=db,
        email=body.email,
        code=body.code,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return schemas.PasswordResetVerifyResponse(
        message=result["message"],
        reset_token=result["reset_token"],
        expires_in_seconds=result["expires_in_seconds"],
    )


@router.post("/reset", response_model=schemas.PasswordResetCompleteResponse)
@limiter.limit("5/minute")
def reset_password(
    request: Request,
    body: schemas.PasswordResetComplete,
    db: Session = Depends(get_db),
) -> schemas.PasswordResetCompleteResponse:
    """
    Complete password reset with new password.

    Rate limited to 5 per minute.

    The new password must meet complexity requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - Not a commonly used password
    - Not found in breach databases

    After successful reset, all existing sessions are invalidated.

    Errors:
    - 400: Invalid token or password doesn't meet requirements
    - 429: Rate limit exceeded
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    language = request.headers.get("Accept-Language", "en")[:2]

    result = PasswordResetService.reset_password(
        db=db,
        email=body.email,
        reset_token=body.reset_token,
        new_password=body.new_password,
        ip_address=ip_address,
        user_agent=user_agent,
        language=language,
    )

    return schemas.PasswordResetCompleteResponse(
        message=result["message"],
    )
