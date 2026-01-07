from datetime import datetime as dt
from datetime import timedelta
from datetime import timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from helpers.pagination import PaginationLimitLarge, PaginationSkip
from helpers.rate_limiter import limiter
from models.exceptions import ValidationException
from repositories.database import get_db
from services import CategoryService, CommentService, IdeaService, UserService
from services.admin_role_service import AdminRoleService

router = APIRouter(prefix="/admin", tags=["admin"])

# Maximum lookback for time-range queries (90 days to prevent DoS)
MAX_QUERY_LOOKBACK_DAYS = 90


@router.get("/ideas/pending", response_model=schemas.PendingIdeasResponse)
def get_pending_ideas(
    skip: PaginationSkip = 0,
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.PendingIdeasResponse:
    """
    Get pending ideas for admin review with pagination.

    Returns paginated list with total count for accurate UI display.
    Domain exceptions are caught by centralized exception handlers.
    """
    ideas = IdeaService.get_pending_ideas_for_admin_with_permissions(
        db, current_user, skip, limit
    )

    total = IdeaService.count_pending_ideas_for_admin_with_permissions(db, current_user)

    return schemas.PendingIdeasResponse(
        items=ideas,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(ideas)) < total,
    )


@router.put("/ideas/{idea_id}/moderate", response_model=schemas.Idea)
def moderate_idea(
    idea_id: int,
    moderation: schemas.IdeaModerate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
):
    """
    Moderate an idea (approve/reject).

    Domain exceptions are caught by centralized exception handlers.
    """
    return IdeaService.moderate_idea_with_permissions(
        db, current_user, idea_id, moderation
    )


@router.get("/comments/all", response_model=List[schemas.Comment])
def get_all_comments(
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Get all comments including moderated ones (admin function)."""
    return CommentService.get_all_comments(db, skip, limit)


@router.put("/comments/{comment_id}/moderate")
def moderate_comment(
    comment_id: int,
    moderation: schemas.CommentUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Moderate a comment."""
    CommentService.moderate_comment(db, comment_id, moderation.is_moderated)
    return {"message": "Comment moderated successfully"}


@router.post("/roles", response_model=schemas.AdminRole)
def create_admin_role(
    role: schemas.AdminRoleCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """
    Create a new admin role.

    Domain exceptions are caught by centralized exception handlers.
    """
    category_id = (
        role.category_id if role.category_id is not None else 0
    )  # Default to 0 if None
    return AdminRoleService.create_admin_role(db, role.user_id, category_id)


@router.get("/roles", response_model=List[schemas.AdminRole])
def get_admin_roles(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """
    Get all admin roles.

    Domain exceptions are caught by centralized exception handlers.
    """
    return AdminRoleService.get_all_admin_roles(db)


@router.delete("/roles/{role_id}")
def delete_admin_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """
    Delete an admin role.

    Domain exceptions are caught by centralized exception handlers.
    """
    AdminRoleService.delete_admin_role(db, role_id)
    return {"message": "Admin role deleted successfully"}


# ============================================================================
# Category Management Endpoints
# ============================================================================


@router.get("/categories", response_model=List[schemas.CategoryStatistics])
def get_all_categories_admin(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Get all categories with statistics."""
    return CategoryService.get_all_categories_with_statistics(db)


@router.post("/categories", response_model=schemas.Category)
def create_category(
    category: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Create a new category."""
    return CategoryService.create_category(db, category)


@router.put("/categories/{category_id}", response_model=schemas.Category)
def update_category(
    category_id: int,
    category_update: schemas.CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Update an existing category."""
    return CategoryService.update_category(db, category_id, category_update)


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Delete a category (only if no ideas are associated)."""
    CategoryService.delete_category(db, category_id)
    return {"message": "Category deleted successfully"}


@router.get("/categories/{category_id}/statistics")
def get_category_statistics(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Get statistics for a category."""
    return CategoryService.get_category_statistics(db, category_id)


# ============================================================================
# User Management Endpoints
# ============================================================================


@router.get("/users", response_model=schemas.UserListResponse)
def get_all_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Users per page"),
    search: Optional[str] = Query(
        None, min_length=1, description="Search by name/email"
    ),
    include_inactive: bool = Query(True),
    role: Optional[str] = Query(
        None,
        description="Filter by role: regular, category_admin, global_admin, official",
        pattern="^(regular|category_admin|global_admin|official)$",
    ),
    is_official: Optional[bool] = Query(None, description="Filter by official status"),
    is_banned: Optional[bool] = Query(None, description="Filter by active ban status"),
    trust_score_min: Optional[int] = Query(
        None, ge=0, le=100, description="Minimum trust score"
    ),
    trust_score_max: Optional[int] = Query(
        None, ge=0, le=100, description="Maximum trust score"
    ),
    vote_score_min: Optional[int] = Query(None, description="Minimum vote score"),
    vote_score_max: Optional[int] = Query(None, description="Maximum vote score"),
    has_penalties: Optional[bool] = Query(
        None, description="Filter users with any penalties"
    ),
    has_active_penalties: Optional[bool] = Query(
        None, description="Filter users with active penalties"
    ),
    created_after: Optional[str] = Query(
        None, description="Registered after date (ISO format)"
    ),
    created_before: Optional[str] = Query(
        None, description="Registered before date (ISO format)"
    ),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Get all users with pagination, search, filtering, and reputation data."""
    import math

    # Parse date strings to datetime objects
    created_after_dt = None
    created_before_dt = None
    if created_after:
        created_after_dt = dt.fromisoformat(created_after.replace("Z", "+00:00"))
    if created_before:
        created_before_dt = dt.fromisoformat(created_before.replace("Z", "+00:00"))

    users, total = UserService.get_users_with_reputation(
        db,
        page=page,
        page_size=page_size,
        search=search,
        include_inactive=include_inactive,
        role=role,
        is_official=is_official,
        is_banned=is_banned,
        trust_score_min=trust_score_min,
        trust_score_max=trust_score_max,
        vote_score_min=vote_score_min,
        vote_score_max=vote_score_max,
        has_penalties=has_penalties,
        has_active_penalties=has_active_penalties,
        created_after=created_after_dt,
        created_before=created_before_dt,
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return schemas.UserListResponse(
        users=[schemas.UserList(**u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Get user details."""
    return UserService.get_user_by_id_or_raise(db, user_id)


@router.put("/users/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Update user properties (is_active, is_global_admin)."""
    return UserService.update_user(db, user_id, user_update)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Delete a user and all associated data."""
    requesting_user_id: int = current_user.id  # type: ignore[assignment]
    UserService.delete_user(db, user_id, requesting_user_id)
    return {"message": "User deleted successfully"}


@router.get("/users/{user_id}/statistics")
def get_user_statistics(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Get detailed statistics for a user."""
    return UserService.get_user_statistics(db, user_id)


# ============================================================================
# Approved Ideas Management
# ============================================================================


@router.get("/ideas/approved", response_model=List[schemas.IdeaWithScore])
def get_approved_ideas(
    category_id: Optional[int] = None,
    quality_key: Optional[str] = Query(
        None,
        description="Filter by quality key (e.g., 'community_benefit', 'would_volunteer')",
    ),
    min_quality_count: int = Query(
        0, ge=0, description="Minimum quality endorsements required"
    ),
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Get all approved ideas for admin management with optional quality filtering."""
    user_id: int = current_user.id  # type: ignore[assignment]
    return IdeaService.get_approved_ideas_for_admin(
        db,
        category_id,
        user_id,
        skip,
        limit,
        quality_key=quality_key,
        min_quality_count=min_quality_count,
    )


@router.post("/ideas/merge", response_model=schemas.Idea)
def merge_ideas(
    merge_request: schemas.IdeaMerge,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Merge duplicate ideas by moving votes and comments."""
    return IdeaService.merge_ideas(
        db, merge_request.source_idea_id, merge_request.target_idea_id
    )


@router.get("/ideas/search")
def search_ideas_admin(
    query: str = Query(..., min_length=2),
    category_id: Optional[int] = None,
    status: Optional[db_models.IdeaStatus] = None,
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Search ideas by keyword (admin)."""
    return IdeaService.search_ideas(db, query, category_id, status, skip, limit)


# ============================================================================
# Deleted Ideas Management (Soft Delete)
# ============================================================================


@router.get(
    "/ideas/deleted",
    response_model=schemas.DeletedIdeasListResponse,
    summary="List deleted ideas",
    description="Get paginated list of deleted ideas for admin review.",
)
def get_deleted_ideas(
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 20,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.DeletedIdeasListResponse:
    """
    Get list of deleted ideas.

    - Admin only
    - Ordered by deletion date (most recent first)
    - Includes deletion metadata (who, when, why)
    """
    ideas, total = IdeaService.get_deleted_ideas(db=db, skip=skip, limit=limit)

    items = [
        schemas.DeletedIdeaSummary(
            id=idea.id,  # type: ignore[arg-type]
            title=str(idea.title),
            status=idea.status,  # type: ignore[arg-type]
            deleted_at=idea.deleted_at,  # type: ignore[arg-type]
            deleted_by_id=idea.deleted_by,  # type: ignore[arg-type]
            deleted_by_name=(
                idea.deleted_by_user.display_name if idea.deleted_by_user else None
            ),
            deletion_reason=idea.deletion_reason,  # type: ignore[arg-type]
            original_author_id=idea.user_id,  # type: ignore[arg-type]
            original_author_name=str(idea.author.display_name),
            created_at=idea.created_at,  # type: ignore[arg-type]
        )
        for idea in ideas
    ]

    return schemas.DeletedIdeasListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


# ============================================================================
# Rejected Ideas Management
# ============================================================================


@router.get(
    "/ideas/rejected",
    response_model=schemas.RejectedIdeasListResponse,
    summary="List rejected ideas",
    description="Get paginated list of rejected ideas for admin review.",
)
def get_rejected_ideas(
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 20,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.RejectedIdeasListResponse:
    """
    Get list of rejected ideas.

    - Admin only
    - Ordered by update date (most recent first)
    - Excludes soft-deleted ideas
    """
    ideas, total = IdeaService.get_rejected_ideas(db=db, skip=skip, limit=limit)

    items = [
        schemas.RejectedIdeaSummary(
            id=idea.id,  # type: ignore[arg-type]
            title=str(idea.title),
            admin_comment=idea.admin_comment,  # type: ignore[arg-type]
            author_id=idea.user_id,  # type: ignore[arg-type]
            author_name=str(idea.author.display_name),
            category_id=idea.category_id,  # type: ignore[arg-type]
            category_name_en=str(idea.category.name_en),
            category_name_fr=str(idea.category.name_fr),
            created_at=idea.created_at,  # type: ignore[arg-type]
        )
        for idea in ideas
    ]

    return schemas.RejectedIdeasListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.delete(
    "/ideas/{idea_id}",
    response_model=schemas.IdeaDeleteResponse,
    summary="Delete an idea (admin)",
    description="Admin can delete any idea. Reason is required for audit trail.",
)
def admin_delete_idea(
    idea_id: int,
    request: schemas.AdminIdeaDeleteRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.IdeaDeleteResponse:
    """
    Admin delete an idea.

    - Admin can delete any idea
    - Reason is required for audit trail
    - Idea can be restored later
    """
    user_id: int = current_user.id  # type: ignore[assignment]

    IdeaService.soft_delete_idea(
        db=db,
        idea_id=idea_id,
        user_id=user_id,
        reason=request.reason,
        is_admin=True,
    )

    return schemas.IdeaDeleteResponse(
        message="Idea deleted by admin",
        idea_id=idea_id,
    )


@router.post(
    "/ideas/{idea_id}/restore",
    response_model=schemas.IdeaRestoreResponse,
    summary="Restore a deleted idea",
    description="Restore a previously deleted idea back to its original status.",
)
def restore_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.IdeaRestoreResponse:
    """
    Restore a deleted idea.

    - Admin only
    - Returns idea to its previous status
    - Clears all deletion metadata
    """
    IdeaService.restore_idea(db=db, idea_id=idea_id)

    return schemas.IdeaRestoreResponse(
        message="Idea restored successfully",
        idea_id=idea_id,
    )


@router.get("/ideas/{idea_id}/statistics")
def get_idea_statistics(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Get detailed statistics for an idea."""
    return IdeaService.get_idea_statistics(db, idea_id)


# ============================================================================
# Comment Management (Moderation)
# ============================================================================


@router.delete("/comments/{comment_id}")
def admin_delete_comment(
    comment_id: int,
    reason: str = Query(..., min_length=10),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Delete a comment (admin)."""
    admin_id: int = current_user.id  # type: ignore[assignment]
    CommentService.admin_delete_comment(db, comment_id, admin_id, reason)
    return {"message": "Comment deleted successfully"}


@router.post("/comments/{comment_id}/restore")
def restore_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Restore a deleted comment."""
    CommentService.restore_comment(db, comment_id)
    return {"message": "Comment restored successfully"}


@router.get("/comments/pending-approval")
def get_pending_approval_comments(
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Get comments pending approval from new users."""
    return CommentService.get_pending_approval_comments(db, skip, limit)


@router.post("/comments/{comment_id}/approve")
def approve_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Approve a pending comment from a new user."""
    admin_id: int = current_user.id  # type: ignore[assignment]
    CommentService.approve_comment(db, comment_id, admin_id)
    return {"message": "Comment approved successfully"}


@router.delete("/comments/{comment_id}/reject")
def reject_pending_comment(
    comment_id: int,
    reason: str = Query("Content not appropriate", min_length=5),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Reject and delete a pending comment."""
    admin_id: int = current_user.id  # type: ignore[assignment]
    CommentService.reject_pending_comment(db, comment_id, admin_id, reason)
    return {"message": "Comment rejected and deleted"}


# ============================================================================
# Official Role Management
# ============================================================================


@router.get("/officials", response_model=List[schemas.OfficialListItem])
def list_officials(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> List[schemas.OfficialListItem]:
    """List all officials (global admin only)."""
    from services.official_service import OfficialService

    officials = OfficialService.get_all_officials(db)
    return [
        schemas.OfficialListItem(
            id=u.id,
            email=u.email,
            username=u.username,
            display_name=u.display_name,
            official_title=u.official_title,
            official_verified_at=u.official_verified_at,
        )
        for u in officials
    ]


@router.post("/officials/grant", response_model=schemas.User)
def grant_official_status(
    grant_data: schemas.OfficialGrant,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.User:
    """Grant official status to a user (global admin only)."""
    from services.official_service import OfficialService

    return OfficialService.grant_official_status(
        db,
        user_id=grant_data.user_id,
        official_title=grant_data.official_title,
        granted_by=current_user,
    )


@router.post("/officials/revoke", response_model=schemas.User)
def revoke_official_status(
    revoke_data: schemas.OfficialRevoke,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.User:
    """Revoke official status from a user (global admin only)."""
    from services.official_service import OfficialService

    return OfficialService.revoke_official_status(
        db,
        user_id=revoke_data.user_id,
        revoked_by=current_user,
    )


@router.put("/officials/{user_id}/title", response_model=schemas.User)
def update_official_title(
    user_id: int,
    title: str = Query(..., min_length=1, max_length=100, description="New title"),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.User:
    """Update an official's title (global admin only)."""
    from services.official_service import OfficialService

    return OfficialService.update_official_title(
        db,
        user_id=user_id,
        official_title=title,
        updated_by=current_user,
    )


@router.get("/officials/requests", response_model=List[schemas.OfficialRequestItem])
def list_official_requests(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> List[schemas.OfficialRequestItem]:
    """List pending official status requests (global admin only)."""
    from services.official_service import OfficialService

    requests = OfficialService.get_pending_official_requests(db)
    return [
        schemas.OfficialRequestItem(
            id=u.id,
            email=u.email,
            username=u.username,
            display_name=u.display_name,
            official_title_request=u.official_title_request,
            official_request_at=u.official_request_at,
        )
        for u in requests
    ]


@router.post("/officials/requests/{user_id}/reject")
def reject_official_request(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """Reject a user's official status request (global admin only)."""
    from services.official_service import OfficialService

    OfficialService.reject_official_request(
        db,
        user_id=user_id,
        rejected_by=current_user,
    )
    return {"message": "Official request rejected"}


# ============================================================================
# Data Retention Management (Law 25 Compliance - Phase 3)
# ============================================================================


@router.get("/retention/status")
def get_retention_status(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """
    Get data retention status for monitoring.

    Admin only endpoint for compliance monitoring.
    Returns counts of pending deletions and anonymizations.
    """
    from services.retention_service import RetentionMetrics

    return RetentionMetrics.get_retention_status(db)


@router.post("/retention/run-cleanup")
def run_retention_cleanup(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """
    Manually trigger retention cleanup.

    Admin only endpoint for manual cleanup when needed.
    Runs all cleanup jobs immediately instead of waiting for scheduler.
    """
    from loguru import logger

    from services.retention_service import RetentionService

    logger.info(f"Manual retention cleanup triggered by admin {current_user.id}")
    results = RetentionService.run_all_cleanup_jobs(db)
    return {
        "status": "completed",
        "results": results,
    }


@router.get("/retention/scheduler")
def get_scheduler_status(
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """
    Get background scheduler status.

    Admin only endpoint to check if retention scheduler is running.
    """
    from core.scheduler import get_scheduler_status

    return get_scheduler_status()


# ============================================================================
# System Diagnostics
# ============================================================================


@router.get(
    "/diagnostics/database",
    response_model=schemas.DatabaseDiagnosticsResponse,
)
def get_database_diagnostics(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.DatabaseDiagnosticsResponse:
    """
    Get database connectivity and table information.

    Admin only endpoint for checking database health,
    especially useful for PostgreSQL deployments.

    Returns:
        - Database type (sqlite/postgresql)
        - Connection status
        - List of tables with row counts
        - Connection pool stats (for PostgreSQL)
    """
    from services.diagnostics_service import DiagnosticsService

    return DiagnosticsService.get_database_diagnostics(db)


@router.get(
    "/diagnostics/system",
    response_model=schemas.SystemResourcesResponse,
)
def get_system_resources(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.SystemResourcesResponse:
    """
    Get system resource usage information.

    Admin only endpoint for monitoring server health:
        - Disk usage (total, used, free, percentage)
        - Docker usage (images, containers, volumes, build cache)
        - Database size (SQLite file or PostgreSQL database)
        - System metrics (uptime, load average, memory usage)

    Note: Docker metrics require the backend to have access to the Docker socket.
    Some metrics may not be available on all platforms.
    """
    from services.diagnostics_service import DiagnosticsService

    return DiagnosticsService.get_system_resources(db)


# ============================================================================
# Security Audit Endpoints (Phase 2)
# ============================================================================


@router.get(
    "/security/events",
    response_model=schemas.AdminSecurityEventsResponse,
    summary="List security events",
    description="Get paginated list of login events with optional filtering.",
)
@limiter.limit("30/minute")
def get_security_events(
    request: Request,
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    event_type: Optional[str] = Query(
        None,
        description="Filter by event type (LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, etc.)",
    ),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    since: Optional[str] = Query(
        None, description="Filter events after this datetime (ISO 8601)"
    ),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.AdminSecurityEventsResponse:
    """
    Get paginated list of security/login events.

    Rate limited to 30 requests/minute to prevent abuse.

    Supports filtering by:
    - event_type: LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, PASSWORD_RESET_REQUEST
    - user_id: specific user's events
    - since: events after a specific datetime (max 90 days lookback)
    """
    from services.security_audit_service import SecurityAuditService

    # Parse and validate since datetime
    since_dt = None
    if since:
        since_dt = dt.fromisoformat(since.replace("Z", "+00:00"))
        # Validate query bounds - reject lookback > 90 days
        min_allowed = dt.now(timezone.utc) - timedelta(days=MAX_QUERY_LOOKBACK_DAYS)
        if since_dt < min_allowed:
            raise ValidationException(
                f"Query lookback cannot exceed {MAX_QUERY_LOOKBACK_DAYS} days"
            )
    else:
        # Default to 7 days if not specified
        since_dt = dt.now(timezone.utc) - timedelta(days=7)

    events, total = SecurityAuditService.get_security_events_list(
        db=db,
        skip=skip,
        limit=limit,
        event_type=event_type,
        user_id=user_id,
        since=since_dt,
    )

    return schemas.AdminSecurityEventsResponse(
        events=events,
        total=total,
        limit=limit,
        offset=skip,
    )


@router.get(
    "/security/summary",
    response_model=schemas.AdminSecuritySummary,
    summary="Security statistics summary",
    description="Get aggregated security statistics for the admin dashboard.",
)
@limiter.limit("30/minute")
def get_security_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.AdminSecuritySummary:
    """
    Get security dashboard summary with:
    - 24-hour event counts (total, successes, failures)
    - Unique IP count
    - Admin login count
    - List of suspicious IPs (high failure rate)
    - Recent admin logins

    Rate limited to 30 requests/minute.
    """
    from services.security_audit_service import SecurityAuditService

    return SecurityAuditService.get_security_summary(db)


@router.get(
    "/security/events/user/{user_id}",
    response_model=schemas.AdminSecurityEventsResponse,
    summary="User's security events",
    description="Get login events for a specific user.",
)
@limiter.limit("20/minute")
def get_user_security_events(
    request: Request,
    user_id: int,
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.AdminSecurityEventsResponse:
    """Get all login/security events for a specific user. Rate limited to 20/minute."""
    from services.security_audit_service import SecurityAuditService

    events, total = SecurityAuditService.get_events_for_user(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )

    return schemas.AdminSecurityEventsResponse(
        events=events,
        total=total,
        limit=limit,
        offset=skip,
    )


@router.get(
    "/security/failed-attempts",
    response_model=schemas.AdminSecurityEventsResponse,
    summary="Failed login attempts",
    description="Get recent failed login attempts.",
)
@limiter.limit("30/minute")
def get_failed_attempts(
    request: Request,
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    hours: int = Query(
        24, ge=1, le=168, description="Time window in hours (max 7 days)"
    ),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.AdminSecurityEventsResponse:
    """Get only failed login attempts within the specified time window. Rate limited to 30/minute."""
    from services.security_audit_service import SecurityAuditService

    # Validate hours doesn't exceed 90 days (2160 hours)
    max_hours = MAX_QUERY_LOOKBACK_DAYS * 24
    if hours > max_hours:
        raise ValidationException(
            f"Time window cannot exceed {MAX_QUERY_LOOKBACK_DAYS} days ({max_hours} hours)"
        )

    events, total = SecurityAuditService.get_failed_attempts_list(
        db=db,
        skip=skip,
        limit=limit,
        hours=hours,
    )

    return schemas.AdminSecurityEventsResponse(
        events=events,
        total=total,
        limit=limit,
        offset=skip,
    )


@router.get(
    "/security/brute-force-risks",
    response_model=schemas.BruteForceRiskResponse,
    summary="Brute force detection",
    description="Detect potential brute force attack patterns.",
)
@limiter.limit("20/minute")
def get_brute_force_risks(
    request: Request,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.BruteForceRiskResponse:
    """
    Detect potential brute force attacks.

    Returns IPs with 3+ failures in the last hour, ranked by failure count.
    Rate limited to 20 requests/minute.
    """
    from services.security_audit_service import SecurityAuditService

    risks = SecurityAuditService.check_brute_force_risk(db)

    return schemas.BruteForceRiskResponse(
        risks=risks,
        count=len(risks),
    )


@router.post(
    "/security/cleanup",
    response_model=schemas.CleanupResponse,
    summary="Trigger event cleanup",
    description="Manually trigger cleanup of old login events.",
)
def trigger_security_cleanup(
    retention_days: int = Query(
        90, ge=30, le=365, description="Days to retain (30-365)"
    ),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.CleanupResponse:
    """
    Manually trigger cleanup of old login events.

    Events older than retention_days will be permanently deleted.
    """
    from services.security_audit_service import SecurityAuditService

    result = SecurityAuditService.trigger_cleanup(db, retention_days=retention_days)

    return schemas.CleanupResponse(
        deleted_count=result["deleted_count"],
        retention_days=result["retention_days"],
        triggered_at=result["triggered_at"],
    )
