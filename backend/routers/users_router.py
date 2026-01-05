"""User profile router endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from repositories.database import get_db
from services.privacy_settings_service import PrivacySettingsService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/profile", response_model=schemas.UserPublicFiltered)
async def get_user_public_profile(
    user_id: int,
    current_user: Optional[db_models.User] = Depends(auth.get_current_user_optional),
    db: Session = Depends(get_db),
) -> schemas.UserPublicFiltered:
    """
    Get user's public profile with privacy settings applied.

    Returns different levels of information based on:
    - Profile visibility setting (public, registered, private)
    - Individual field visibility settings
    - Whether the requester is logged in

    Law 25 Compliance: Article 9.1 (Privacy by Default), Article 10 (User Control)
    """
    return PrivacySettingsService.get_public_profile(
        db=db,
        target_user_id=user_id,
        requesting_user=current_user,
    )
