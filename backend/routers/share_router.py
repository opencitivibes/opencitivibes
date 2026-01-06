"""
Share router for API endpoints.

Handles share event recording and analytics retrieval.
No authentication required for recording shares (fire-and-forget).
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from repositories.database import get_db
from services.share_service import ShareService

router = APIRouter(prefix="/shares", tags=["shares"])


@router.post(
    "/{idea_id}",
    response_model=schemas.ShareEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_share(
    idea_id: int,
    share_data: schemas.ShareEventCreate,
    db: Session = Depends(get_db),
):
    """
    Record a share event for an idea.

    No authentication required - fire-and-forget tracking.

    - **idea_id**: ID of the idea being shared
    - **platform**: Social media platform (twitter, facebook, linkedin, whatsapp, copy_link)
    - **referrer_url**: Optional URL where share was initiated
    """
    return ShareService.record_share(
        db=db,
        idea_id=idea_id,
        platform=share_data.platform,
        referrer_url=share_data.referrer_url,
    )


@router.get("/{idea_id}/analytics", response_model=schemas.ShareAnalyticsResponse)
def get_share_analytics(
    idea_id: int,
    db: Session = Depends(get_db),
):
    """
    Get share analytics for a specific idea.

    Public endpoint - no authentication required.

    Returns total shares, breakdown by platform, and shares in last 7 days.
    """
    return ShareService.get_idea_share_analytics(db=db, idea_id=idea_id)


# Admin endpoints
admin_router = APIRouter(prefix="/admin/analytics", tags=["admin", "analytics"])


@admin_router.get("/shares", response_model=schemas.AdminShareAnalyticsResponse)
def get_admin_share_analytics(
    db: Session = Depends(get_db),
    _current_admin: db_models.User = Depends(auth.get_admin_user),
):
    """
    Get admin share analytics overview.

    Requires global admin privileges.

    Returns:
    - Total shares across all ideas
    - Platform distribution
    - Top shared ideas
    - Shares in last 7 and 30 days
    """
    return ShareService.get_admin_share_analytics(db=db)
