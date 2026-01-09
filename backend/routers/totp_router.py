"""Router for 2FA TOTP endpoints."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from helpers.rate_limiter import limiter
from repositories.database import get_db
from services.totp_service import TOTPService

router = APIRouter(prefix="/auth/2fa", tags=["2FA"])


@router.post("/setup", response_model=schemas.TwoFactorSetupResponse)
async def setup_2fa(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.TwoFactorSetupResponse:
    """
    Initialize 2FA setup.

    Returns secret and provisioning URI for QR code.
    User must verify with a code before 2FA is active.
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    return TOTPService.setup_2fa(db, user_id)


@router.post("/verify-setup", response_model=schemas.TwoFactorVerifySetupResponse)
async def verify_setup(
    request_body: schemas.TwoFactorVerifySetupRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.TwoFactorVerifySetupResponse:
    """
    Complete 2FA setup by verifying first code.

    Returns backup codes (show to user once, they cannot be retrieved again).
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    return TOTPService.verify_setup(db, user_id, request_body.code)


@router.delete("/disable", response_model=schemas.MessageResponse)
async def disable_2fa(
    request_body: schemas.TwoFactorDisableRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.MessageResponse:
    """
    Disable 2FA for account.

    Requires password or email verification code for security.
    """
    return TOTPService.disable_2fa(
        db,
        current_user,
        password=request_body.password,
        email_code=request_body.email_code,
    )


@router.get("/status", response_model=schemas.TwoFactorStatusResponse)
async def get_2fa_status(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.TwoFactorStatusResponse:
    """Get current 2FA status for user."""
    user_id: int = current_user.id  # type: ignore[assignment]
    return TOTPService.get_status(db, user_id)


@router.post(
    "/verify",
    response_model=schemas.Token | schemas.TokenWithDeviceToken,
)
@limiter.limit("10/minute")
async def verify_2fa_login(
    request: Request,
    response: Response,
    request_body: schemas.TwoFactorLoginRequest,
    db: Session = Depends(get_db),
) -> schemas.Token | schemas.TokenWithDeviceToken:
    """
    Complete login with 2FA code.

    Called after initial authentication returns a temp_token indicating 2FA is required.

    If trust_device=True and consent_given=True, a device_token will be set as
    an httpOnly cookie for security (XSS protection) and also returned in the
    response body for mobile app clients.

    SECURITY: httpOnly cookie prevents XSS theft of device tokens.
    """
    from helpers.request_utils import (
        get_client_ip,
        get_user_agent,
        set_device_token_cookie,
    )
    from models.config import settings

    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    result = TOTPService.verify_2fa_login(
        db,
        request_body.temp_token,
        request_body.code,
        request_body.is_backup_code,
        ip_address=ip_address,
        user_agent=user_agent,
        trust_device=request_body.trust_device,
        trust_duration_days=request_body.trust_duration_days,
        consent_given=request_body.consent_given,
    )

    # SECURITY: Set httpOnly cookie for device token (XSS protection)
    if (
        isinstance(result, schemas.TokenWithDeviceToken)
        and result.device_token
        and result.device_expires_at
    ):
        set_device_token_cookie(
            response=response,
            device_token=result.device_token,
            expires_at=result.device_expires_at,
            is_production=(settings.ENVIRONMENT == "production"),
        )

    # SECURITY: Add cache-control header to prevent token caching
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["X-Content-Type-Options"] = "nosniff"

    return result


@router.post("/backup-codes/regenerate", response_model=schemas.BackupCodesResponse)
async def regenerate_backup_codes(
    request_body: schemas.TwoFactorDisableRequest,  # Same re-auth requirement
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.BackupCodesResponse:
    """
    Generate new set of backup codes.

    Warning: This invalidates all existing backup codes.
    Requires password or email verification for security.
    """
    return TOTPService.regenerate_backup_codes(
        db,
        current_user,
        password=request_body.password,
        email_code=request_body.email_code,
    )


@router.get("/backup-codes/count", response_model=schemas.BackupCodesCountResponse)
async def get_backup_codes_count(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.BackupCodesCountResponse:
    """Get count of remaining unused backup codes."""
    user_id: int = current_user.id  # type: ignore[assignment]
    remaining = TOTPService.get_backup_codes_count(
        db, user_id, bool(current_user.totp_enabled)
    )
    return schemas.BackupCodesCountResponse(remaining=remaining)


# ============================================================================
# Trusted Device Management (2FA Remember Device - Law 25 Compliance)
# ============================================================================


@router.get("/devices", response_model=schemas.TrustedDeviceListResponse)
@limiter.limit("30/minute")
async def list_trusted_devices(
    request: Request,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.TrustedDeviceListResponse:
    """
    List all trusted devices for the current user.

    Law 25 Compliance: Right to Access (Article 27)
    Users can view all devices that have been trusted to bypass 2FA.
    """
    from services.trusted_device_service import TrustedDeviceService

    user_id: int = current_user.id  # type: ignore[assignment]

    # Get devices from service
    devices = TrustedDeviceService.get_user_devices(db, user_id)

    # Convert to response schemas
    device_responses = [
        schemas.TrustedDeviceResponse(
            id=device.id,
            device_name=str(device.device_name),
            trusted_at=device.trusted_at,
            expires_at=device.expires_at,
            last_used_at=device.last_used_at,
            is_active=bool(device.is_active),
        )
        for device in devices
    ]

    return schemas.TrustedDeviceListResponse(
        devices=device_responses,
        total=len(device_responses),
    )


@router.patch(
    "/devices/{device_id}",
    response_model=schemas.TrustedDeviceResponse,
)
@limiter.limit("10/minute")
async def rename_trusted_device(
    request: Request,
    device_id: int,
    rename_request: schemas.TrustedDeviceRename,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.TrustedDeviceResponse:
    """
    Rename a trusted device.

    Allows users to give their devices friendly names for easier management.
    """
    from services.trusted_device_service import TrustedDeviceService

    user_id: int = current_user.id  # type: ignore[assignment]

    device = TrustedDeviceService.rename_device(
        db,
        user_id,
        device_id,
        rename_request.device_name,
    )

    return schemas.TrustedDeviceResponse(
        id=device.id,
        device_name=str(device.device_name),
        trusted_at=device.trusted_at,
        expires_at=device.expires_at,
        last_used_at=device.last_used_at,
        is_active=bool(device.is_active),
    )


@router.delete("/devices/{device_id}", response_model=schemas.MessageResponse)
@limiter.limit("10/minute")
async def revoke_trusted_device(
    request: Request,
    device_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.MessageResponse:
    """
    Revoke trust for a specific device.

    Law 25 Compliance: Right to Withdraw Consent (Article 9.1)
    The revoked device will be required to complete 2FA on next login.
    """
    from helpers.request_utils import get_client_ip, get_user_agent
    from services.trusted_device_service import TrustedDeviceService

    user_id: int = current_user.id  # type: ignore[assignment]
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    TrustedDeviceService.revoke_device(
        db,
        user_id,
        device_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return schemas.MessageResponse(message="Device trust revoked successfully")


@router.delete("/devices", response_model=schemas.MessageResponse)
@limiter.limit("5/minute")
async def revoke_all_trusted_devices(
    request: Request,
    password_confirmation: schemas.PasswordConfirmation,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.MessageResponse:
    """
    Revoke trust for all devices.

    SECURITY: Requires password confirmation to prevent CSRF attacks.

    Law 25 Compliance: Right to Withdraw Consent (Article 9.1)
    All devices will be required to complete 2FA on next login.
    Useful for security concerns or password changes.
    """
    from helpers.request_utils import get_client_ip, get_user_agent
    from models.exceptions import InvalidCredentialsException
    from services.trusted_device_service import TrustedDeviceService

    # SECURITY: Verify password to prevent CSRF attacks on bulk revocation
    if not auth.verify_password(
        password_confirmation.password, current_user.hashed_password
    ):
        raise InvalidCredentialsException("Invalid password")

    user_id: int = current_user.id  # type: ignore[assignment]
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    count = TrustedDeviceService.revoke_all_devices(
        db,
        user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return schemas.MessageResponse(message=f"Revoked trust for {count} device(s)")
