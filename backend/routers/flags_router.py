"""
Router for content flag endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from helpers.pagination import PaginationLimit, PaginationSkip
from repositories.database import get_db
from services.flag_service import FlagService

router = APIRouter(prefix="/flags", tags=["flags"])


@router.post("", response_model=schemas.FlagResponse)
def create_flag(
    flag_data: schemas.FlagCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> db_models.ContentFlag:
    """
    Flag inappropriate content.

    Users can flag comments or ideas they find inappropriate.
    One flag per user per content item.

    Domain exceptions are caught by centralized exception handlers.
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    return FlagService.create_flag(
        db=db,
        content_type=flag_data.content_type,
        content_id=flag_data.content_id,
        reporter_id=user_id,
        reason=flag_data.reason,
        details=flag_data.details,
    )


@router.get("/my-flags", response_model=list[schemas.FlagResponse])
def get_my_flags(
    skip: Annotated[PaginationSkip, PaginationSkip] = 0,
    limit: Annotated[PaginationLimit, PaginationLimit] = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> list[db_models.ContentFlag]:
    """
    Get flags submitted by current user.

    Returns list of all flags the user has submitted, ordered by date.
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    return FlagService.get_user_flags(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )


@router.delete("/{flag_id}")
def retract_flag(
    flag_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> dict[str, str]:
    """
    Retract a flag.

    Users can retract their own flags only if not yet reviewed.

    Domain exceptions are caught by centralized exception handlers.
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    FlagService.retract_flag(
        db=db,
        flag_id=flag_id,
        user_id=user_id,
    )
    return {"message": "Flag retracted successfully"}


@router.get("/check/{content_type}/{content_id}")
def check_flag_status(
    content_type: db_models.ContentType,
    content_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> dict[str, bool]:
    """
    Check if current user has flagged specific content.

    Used to show/hide flag button in UI.
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    already_flagged = FlagService.check_user_already_flagged(
        db=db,
        content_type=content_type,
        content_id=content_id,
        user_id=user_id,
    )
    return {"flagged": already_flagged}
