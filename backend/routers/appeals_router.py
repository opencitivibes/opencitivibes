"""
Router for appeal endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from helpers.pagination import PaginationLimit, PaginationSkip
from repositories.database import get_db
from services.appeal_service import AppealService

router = APIRouter(prefix="/appeals", tags=["appeals"])


@router.post("", response_model=schemas.AppealResponse)
def submit_appeal(
    appeal_data: schemas.AppealCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_user),
) -> schemas.AppealResponse:
    """
    Submit an appeal for a penalty.

    Banned users can still access this endpoint to appeal their ban.
    Note: Uses get_current_user (not get_current_active_user) to allow
    banned users to submit appeals.

    Domain exceptions are caught by centralized exception handlers.
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    appeal = AppealService.submit_appeal(
        db=db,
        penalty_id=appeal_data.penalty_id,
        user_id=user_id,
        reason=appeal_data.reason,
    )
    return schemas.AppealResponse.model_validate(appeal)


@router.get("/my-appeals", response_model=list[schemas.AppealResponse])
def get_my_appeals(
    skip: PaginationSkip = 0,
    limit: PaginationLimit = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_user),
) -> list[schemas.AppealResponse]:
    """
    Get appeals submitted by current user.

    Banned users can access this to check appeal status.
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    appeals = AppealService.get_user_appeals(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )
    return [schemas.AppealResponse.model_validate(appeal) for appeal in appeals]
