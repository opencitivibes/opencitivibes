"""Parental Consent Router (Law 25 Minors Compliance).

Public endpoints for parents to verify and respond to consent requests.
Token serves as authentication - no login required.

Security considerations:
- Tokens are single-use
- IP and User-Agent logged for audit
- Rate limiting on resend endpoint
- Token expires after 7 days
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

import models.schemas as schemas
from helpers.rate_limiter import limiter
from repositories.database import get_db
from services.email_service import EmailService
from services.parental_consent_service import ParentalConsentService

router = APIRouter(prefix="/parental-consent", tags=["parental-consent"])


# ============================================================================
# Public Endpoints (Token is Auth)
# ============================================================================


@router.get("/verify/{token}", response_model=schemas.ConsentDetailsResponse)
async def verify_consent_token(
    token: str,
    db: Session = Depends(get_db),
) -> schemas.ConsentDetailsResponse:
    """
    Verify parental consent token and get request details.

    Called when parent clicks email link.
    Returns child's info and consent form data for Law 25 disclosure.

    No authentication required - token serves as authentication.
    """
    details = ParentalConsentService.get_consent_details(db, token)
    return schemas.ConsentDetailsResponse(
        child_username=details["child_username"],
        child_email=details["child_email"],
        child_age=details.get("child_age"),
        child_display_name=details.get("child_display_name"),
        requested_at=details["requested_at"],
        expires_at=details["expires_at"],
        parent_email=details["parent_email"],
        data_collected=details["data_collected"],
        data_purposes=details["data_purposes"],
        retention_period=details["retention_period"],
        parent_rights=details["parent_rights"],
    )


@router.post("/grant/{token}", response_model=schemas.MessageResponse)
async def grant_consent(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> schemas.MessageResponse:
    """
    Parent grants consent for child's account.

    Account is activated immediately.
    IP and User-Agent are logged for audit trail.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:500]

    user = ParentalConsentService.grant_consent(
        db=db,
        token=token,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Send confirmation email to parent
    EmailService.send_consent_granted_notification(
        to_email=str(user.parent_email),
        child_username=str(user.username),
        language="fr",  # Default to French for Quebec Law 25
    )

    return schemas.MessageResponse(
        message=f"Consent granted. Account '{user.username}' is now active."
    )


@router.post("/deny/{token}", response_model=schemas.MessageResponse)
async def deny_consent(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> schemas.MessageResponse:
    """
    Parent denies consent for child's account.

    Account will be deleted after 30-day grace period.
    IP and User-Agent are logged for audit trail.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:500]

    user = ParentalConsentService.deny_consent(
        db=db,
        token=token,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Send notification email to parent
    EmailService.send_consent_denied_notification(
        to_email=str(user.parent_email),
        child_username=str(user.username),
        language="fr",  # Default to French for Quebec Law 25
    )

    return schemas.MessageResponse(
        message="Consent denied. Account will be deleted in 30 days."
    )


@router.post("/resend/{user_id}", response_model=schemas.MessageResponse)
@limiter.limit("3/day")
async def resend_consent_email(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
) -> schemas.MessageResponse:
    """
    Resend parental consent email for pending account.

    Rate limited to 3 resends per day per user (enforced at both
    application level and service level).

    No auth required - parent may not have login.
    Requires valid pending user_id.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:500]

    token, plain_token = ParentalConsentService.resend_consent_request(
        db=db,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Get consent URL from config
    from models.config import settings
    from helpers.age_utils import calculate_age
    from services import UserService

    user = UserService.get_user_by_id(db, user_id)

    if user and user.date_of_birth:
        consent_url = f"{settings.APP_URL}/consent/{plain_token}"
        child_age = calculate_age(user.date_of_birth)

        EmailService.send_parental_consent_request(
            to_email=token.parent_email,
            child_username=str(user.username),
            child_email=str(user.email),
            child_age=child_age,
            consent_url=consent_url,
            expires_at=token.expires_at,
            language="fr",  # Default to French for Quebec Law 25
        )

    return schemas.MessageResponse(message="Consent email sent successfully.")
