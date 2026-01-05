"""Authentication router endpoints."""

from typing import Union

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from helpers.rate_limiter import limiter
from repositories.database import get_db
from services import UserService
from services.auth_service import AuthService
from services.totp_service import TOTPService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.User)
@limiter.limit("3/minute")
def register(
    request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)
) -> db_models.User:
    """
    Register a new user.

    Requires explicit consent to Terms of Service and Privacy Policy.
    Rate limited to 3 per minute.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:500]

    return UserService.register_user(
        db=db,
        user_data=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post(
    "/login",
    response_model=Union[schemas.Token, schemas.TwoFactorRequiredResponse],
)
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Union[schemas.Token, schemas.TwoFactorRequiredResponse]:
    """
    Login user. Rate limited to 5 per minute.

    If user has 2FA enabled, returns TwoFactorRequiredResponse with temp_token.
    Call /auth/2fa/verify with the temp_token and TOTP code to complete login.

    Domain exceptions are caught by centralized exception handlers.
    """
    return TOTPService.login_with_2fa_check(db, form_data.username, form_data.password)


@router.post("/refresh", response_model=schemas.Token)
async def refresh_token(
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.Token:
    """
    Refresh the access token.

    Returns a new access token with a fresh expiration time.
    The user must have a valid (not expired) token to refresh.
    """
    return AuthService.refresh_token(current_user)


@router.get("/me", response_model=schemas.User)
async def read_users_me(
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> db_models.User:
    """Get current user."""
    return current_user


@router.put("/profile", response_model=schemas.User)
async def update_profile(
    profile_update: schemas.UserProfileUpdate,
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> db_models.User:
    """Update user profile (display_name, email)."""
    user_id: int = current_user.id  # type: ignore[assignment]
    return UserService.update_profile(db, user_id, profile_update)


@router.put("/password")
async def change_password(
    password_change: schemas.PasswordChange,
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Change user password."""
    user_id: int = current_user.id  # type: ignore[assignment]
    UserService.change_password(
        db,
        user_id,
        password_change.current_password,
        password_change.new_password,
    )
    return {"message": "Password changed successfully"}


@router.get("/activity", response_model=schemas.UserActivityHistory)
async def get_activity_history(
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> schemas.UserActivityHistory:
    """Get user activity history."""
    user_id: int = current_user.id  # type: ignore[assignment]
    return UserService.get_activity_history(db, user_id)


@router.post("/avatar", response_model=schemas.AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> schemas.AvatarUploadResponse:
    """Upload user avatar."""
    user_id: int = current_user.id  # type: ignore[assignment]
    return UserService.upload_avatar(db, user_id, file)


# ============================================================================
# Consent Management Endpoints (Law 25 Compliance)
# ============================================================================


@router.get("/consent", response_model=schemas.ConsentStatus)
async def get_consent_status(
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> schemas.ConsentStatus:
    """
    Get current user's consent status.

    Returns whether user needs to re-consent due to policy updates.
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    return UserService.get_consent_status(db, user_id)


@router.put("/consent", response_model=schemas.ConsentStatus)
async def update_consent(
    request: Request,
    consent_update: schemas.ConsentUpdate,
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> schemas.ConsentStatus:
    """
    Update user consent preferences.

    Allows users to:
    - Withdraw/grant marketing consent
    - Re-accept terms/privacy after policy updates

    Law 25 Compliance: Consent withdrawal must be as easy as giving consent.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:500]
    user_id: int = current_user.id  # type: ignore[assignment]

    return UserService.update_consent(
        db=db,
        user_id=user_id,
        consent_update=consent_update,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.get("/consent/history", response_model=list[schemas.ConsentLogExport])
async def get_consent_history(
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> list[schemas.ConsentLogExport]:
    """
    Get current user's consent history.

    Law 25 Compliance: Users have the right to access all their personal data,
    including the history of consent changes.
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    return UserService.get_consent_history(db, user_id)


# ============================================================================
# Data Rights Endpoints (Law 25 Compliance - Phase 2)
# ============================================================================


@router.get("/export-data")
@limiter.limit("3/hour")
async def export_my_data(
    request: Request,
    format: str = "json",
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> schemas.UserDataExport:
    """
    Export all user data in machine-readable format.

    Law 25 Compliance: Article 27 (Access) and Article 28.1 (Portability)

    Returns user's complete personal data including:
    - Profile information
    - Ideas submitted
    - Comments made
    - Votes cast
    - Consent history

    Rate limited to 3 requests per hour to prevent abuse.

    Args:
        format: Export format ('json' or 'csv')

    Returns:
        Complete user data export
    """
    from services.data_export_service import DataExportService

    if format not in ("json", "csv"):
        format = "json"

    user_id: int = current_user.id  # type: ignore[assignment]
    data = DataExportService.export_user_data(
        db=db,
        user_id=user_id,
        export_format=format,
    )

    # For CSV, return as streaming response
    if format == "csv":
        from fastapi.responses import StreamingResponse

        return StreamingResponse(  # type: ignore[return-value, arg-type]
            iter([data]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=my_data_{user_id}.csv"
            },
        )

    # For JSON, convert dict to schema
    return schemas.UserDataExport(
        export_date=data["export_date"],  # type: ignore[arg-type]
        export_format=data["export_format"],  # type: ignore[arg-type]
        user_profile=schemas.UserProfileExport(**data["user_profile"]),  # type: ignore[arg-type]
        ideas=[schemas.IdeaExport(**idea) for idea in data["ideas"]],  # type: ignore[arg-type]
        comments=[schemas.CommentExport(**comment) for comment in data["comments"]],  # type: ignore[arg-type]
        votes=[schemas.VoteExport(**vote) for vote in data["votes"]],  # type: ignore[arg-type]
        consent_history=[
            schemas.ConsentLogExport(**log)  # type: ignore[arg-type]
            for log in data["consent_history"]  # type: ignore[arg-type]
        ],
    )


@router.delete("/account", response_model=schemas.DeleteAccountResponse)
@limiter.limit("3/day")
async def delete_my_account(
    request: Request,
    delete_request: schemas.DeleteAccountRequest,
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> schemas.DeleteAccountResponse:
    """
    Delete user's own account (self-service).

    Law 25 Compliance: Article 28 (Right to Erasure)

    Requires:
    - Current password for verification
    - Confirmation text 'DELETE MY ACCOUNT'

    Options:
    - delete_content=False (default): Anonymize content, keep for community
    - delete_content=True: Remove all user content

    This action is irreversible. User data will be anonymized or deleted
    according to the chosen option.
    """
    from services.account_deletion_service import AccountDeletionService

    ip_address = request.client.host if request.client else None
    user_id: int = current_user.id  # type: ignore[assignment]

    return AccountDeletionService.delete_account(
        db=db,
        user_id=user_id,
        request=delete_request,
        ip_address=ip_address,
    )


# ============================================================================
# Privacy Settings Endpoints (Law 25 Compliance - Phase 4)
# ============================================================================


@router.get("/privacy-settings", response_model=schemas.PrivacySettings)
async def get_privacy_settings(
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> schemas.PrivacySettings:
    """
    Get current user's privacy settings.

    Law 25 Compliance: Article 10 (User Control)
    """
    from services.privacy_settings_service import PrivacySettingsService

    user_id: int = current_user.id  # type: ignore[assignment]
    return PrivacySettingsService.get_privacy_settings(db, user_id)


@router.put("/privacy-settings", response_model=schemas.PrivacySettings)
async def update_privacy_settings(
    settings_update: schemas.PrivacySettingsUpdate,
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> schemas.PrivacySettings:
    """
    Update current user's privacy settings.

    Law 25 Compliance: Article 9.1 (Privacy by Default), Article 10 (User Control)

    Available settings:
    - profile_visibility: public, registered, private
    - show_display_name: true/false
    - show_avatar: true/false
    - show_activity: true/false
    - show_join_date: true/false
    """
    from services.privacy_settings_service import PrivacySettingsService

    user_id: int = current_user.id  # type: ignore[assignment]
    return PrivacySettingsService.update_privacy_settings(
        db=db,
        user_id=user_id,
        settings_update=settings_update,
    )


# ============================================================================
# Policy Version Endpoints (Law 25 Compliance - Phase 4)
# ============================================================================


@router.get("/policy/reconsent-check", response_model=schemas.ReconsentCheck)
async def check_reconsent_required(
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> schemas.ReconsentCheck:
    """
    Check if user needs to re-consent to updated policies.

    Law 25 Compliance: Article 8.1 (Inform of policy changes)
    """
    from services.policy_service import PolicyService

    return PolicyService.check_requires_reconsent(db, current_user)


@router.get(
    "/policy/changelog/{policy_type}", response_model=schemas.PolicyChangelogResponse
)
async def get_policy_changelog(
    policy_type: str,
    since_version: str | None = None,
    db: Session = Depends(get_db),
) -> schemas.PolicyChangelogResponse:
    """
    Get changelog of policy versions.

    Args:
        policy_type: 'privacy' or 'terms'
        since_version: Show changes since this version (optional)

    Returns:
        List of policy version changes with summaries
    """
    from services.policy_service import PolicyService

    return PolicyService.get_policy_changelog(db, policy_type, since_version)


@router.post("/policy/reconsent", response_model=schemas.MessageResponse)
async def record_reconsent(
    request: Request,
    reconsent: schemas.ReconsentRequest,
    current_user: db_models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
) -> schemas.MessageResponse:
    """
    Record user's re-consent to an updated policy.

    Law 25 Compliance: Article 9 (Explicit consent)
    """
    from services.policy_service import PolicyService

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:500]

    PolicyService.record_reconsent(
        db=db,
        user=current_user,
        policy_type=reconsent.policy_type,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return schemas.MessageResponse(
        message=f"Successfully re-consented to {reconsent.policy_type} policy"
    )
