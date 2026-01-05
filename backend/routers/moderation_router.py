"""
Router for admin moderation endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from helpers.pagination import PaginationLimitLarge, PaginationSkip
from repositories.database import get_db
from services.admin_note_service import AdminNoteService
from services.appeal_service import AppealService
from services.moderation_service import ModerationService
from services.moderation_stats_service import ModerationStatsService
from services.penalty_service import PenaltyService
from services.watchlist_service import WatchlistService

router = APIRouter(prefix="/admin/moderation", tags=["admin-moderation"])


# ============================================================================
# Moderation Queue Endpoints
# ============================================================================


@router.get("/queue", response_model=schemas.ModerationQueueResponse)
def get_moderation_queue(
    content_type: Optional[db_models.ContentType] = None,
    reason: Optional[db_models.FlagReason] = None,
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """
    Get moderation queue with flagged content.

    Filters by content type and/or flag reason.
    Sorted by flag count (most flagged first).
    """
    items, total, pending = ModerationService.get_moderation_queue(
        db, content_type, reason, skip, limit
    )
    return {
        "items": items,
        "total": total,
        "pending_count": pending,
    }


@router.get("/flags/{content_type}/{content_id}")
def get_flags_for_content(
    content_type: db_models.ContentType,
    content_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> list:
    """Get all flags for specific content."""
    from services.flag_service import FlagService

    return FlagService.get_flags_for_content(
        db, content_type, content_id, include_reviewed=True
    )


@router.post("/review")
def review_flags(
    review_data: schemas.FlagReview,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """
    Review flags and take action.

    Actions:
    - dismiss: Dismiss flags, unhide content
    - action: Delete content, update trust scores, optionally issue penalty
    """
    admin_id: int = current_user.id  # type: ignore[assignment]
    return ModerationService.review_flags(
        db=db,
        flag_ids=review_data.flag_ids,
        action=review_data.action,
        reviewer_id=admin_id,
        review_notes=review_data.review_notes,
        issue_penalty=review_data.issue_penalty,
        penalty_type=review_data.penalty_type,
        penalty_reason=review_data.penalty_reason,
    )


@router.get("/flagged-users", response_model=schemas.FlaggedUsersResponse)
def get_flagged_users(
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """Get users with pending flagged content."""
    users, total = ModerationService.get_flagged_users(db, skip, limit)
    return {"users": users, "total": total}


@router.get("/stats", response_model=schemas.ModerationStats)
def get_moderation_stats(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.ModerationStats:
    """Get moderation statistics dashboard."""
    return ModerationStatsService.get_moderation_stats(db)


# ============================================================================
# Penalty Endpoints
# ============================================================================


@router.post("/penalties", response_model=schemas.PenaltyResponse)
def issue_penalty(
    penalty_data: schemas.PenaltyCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Issue a penalty to a user."""
    admin_id: int = current_user.id  # type: ignore[assignment]
    return PenaltyService.issue_penalty(
        db=db,
        user_id=penalty_data.user_id,
        penalty_type=penalty_data.penalty_type,
        reason=penalty_data.reason,
        issued_by=admin_id,
        related_flag_ids=penalty_data.related_flag_ids,
        bulk_delete_content=penalty_data.bulk_delete_content,
    )


@router.get("/penalties")
def get_all_penalties(
    penalty_type: Optional[db_models.PenaltyType] = None,
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """Get all active penalties."""
    penalties, total = PenaltyService.get_all_active_penalties(
        db, penalty_type, skip, limit
    )
    return {"penalties": penalties, "total": total}


@router.get("/penalties/user/{user_id}")
def get_user_penalties(
    user_id: int,
    include_expired: bool = Query(True),
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> list:
    """Get all penalties for a specific user."""
    return PenaltyService.get_user_penalties(db, user_id, include_expired, skip, limit)


@router.put("/penalties/{penalty_id}/revoke", response_model=schemas.PenaltyResponse)
def revoke_penalty(
    penalty_id: int,
    revoke_data: schemas.PenaltyRevoke,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Revoke an active penalty."""
    admin_id: int = current_user.id  # type: ignore[assignment]
    return PenaltyService.revoke_penalty(db, penalty_id, admin_id, revoke_data.reason)


# ============================================================================
# Appeal Endpoints
# ============================================================================


@router.get("/appeals")
def get_pending_appeals(
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """Get pending appeals for review."""
    appeals, total = AppealService.get_pending_appeals(db, skip, limit)
    return {"appeals": appeals, "total": total}


@router.put("/appeals/{appeal_id}", response_model=schemas.AppealResponse)
def review_appeal(
    appeal_id: int,
    review_data: schemas.AppealReview,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Review and decide on an appeal."""
    admin_id: int = current_user.id  # type: ignore[assignment]
    return AppealService.review_appeal(
        db, appeal_id, admin_id, review_data.action, review_data.review_notes
    )


# ============================================================================
# Admin Notes Endpoints
# ============================================================================


@router.get("/notes/user/{user_id}", response_model=list[schemas.AdminNoteResponse])
def get_user_notes(
    user_id: int,
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> list:
    """Get admin notes for a user."""
    return AdminNoteService.get_notes_for_user(db, user_id, skip, limit)


@router.post("/notes/user/{user_id}", response_model=schemas.AdminNoteResponse)
def add_user_note(
    user_id: int,
    note_data: schemas.AdminNoteCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """Add an admin note to a user profile."""
    admin_id: int = current_user.id  # type: ignore[assignment]
    return AdminNoteService.add_note(db, user_id, note_data.content, admin_id)


@router.put("/notes/{note_id}", response_model=schemas.AdminNoteResponse)
def update_note(
    note_id: int,
    note_data: schemas.AdminNoteUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """Update an admin note."""
    admin_id: int = current_user.id  # type: ignore[assignment]
    return AdminNoteService.update_note(db, note_id, note_data.content, admin_id)


@router.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """Delete an admin note."""
    admin_id: int = current_user.id  # type: ignore[assignment]
    AdminNoteService.delete_note(db, note_id, admin_id)
    return {"message": "Note deleted successfully"}


# ============================================================================
# Keyword Watchlist Endpoints
# ============================================================================


@router.get("/watchlist", response_model=list[schemas.KeywordResponse])
def get_watchlist(
    active_only: bool = Query(False),
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 100,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> list:
    """Get keyword watchlist."""
    return WatchlistService.get_all_keywords(db, active_only, skip, limit)


@router.post("/watchlist", response_model=schemas.KeywordResponse)
def add_keyword(
    keyword_data: schemas.KeywordCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Add a keyword to the watchlist."""
    admin_id: int = current_user.id  # type: ignore[assignment]
    return WatchlistService.add_keyword(
        db,
        keyword_data.keyword,
        admin_id,
        keyword_data.is_regex,
        keyword_data.auto_flag_reason,
    )


@router.put("/watchlist/{keyword_id}", response_model=schemas.KeywordResponse)
def update_keyword(
    keyword_id: int,
    keyword_data: schemas.KeywordUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Update a keyword in the watchlist."""
    return WatchlistService.update_keyword(
        db,
        keyword_id,
        keyword_data.is_regex,
        keyword_data.auto_flag_reason,
        keyword_data.is_active,
    )


@router.delete("/watchlist/{keyword_id}")
def delete_keyword(
    keyword_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """Delete a keyword from the watchlist."""
    WatchlistService.delete_keyword(db, keyword_id)
    return {"message": "Keyword deleted successfully"}


@router.post("/watchlist/test")
def test_keyword(
    test_data: dict,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """Test a keyword against sample text."""
    keyword = test_data.get("keyword", "")
    test_text = test_data.get("test_text", "")
    matches = WatchlistService.test_keyword(keyword, test_text)
    return {"matches": matches}
