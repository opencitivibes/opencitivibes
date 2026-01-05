"""Router for 2FA TOTP endpoints."""

from fastapi import APIRouter, Depends, Request
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


@router.post("/verify", response_model=schemas.Token)
@limiter.limit("10/minute")
async def verify_2fa_login(
    request: Request,
    request_body: schemas.TwoFactorLoginRequest,
    db: Session = Depends(get_db),
) -> schemas.Token:
    """
    Complete login with 2FA code.

    Called after initial authentication returns a temp_token indicating 2FA is required.
    """
    return TOTPService.verify_2fa_login(
        db,
        request_body.temp_token,
        request_body.code,
        request_body.is_backup_code,
    )


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
