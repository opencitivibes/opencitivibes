"""
Tags router for tag-related endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import repositories.db_models as db_models
import models.schemas as schemas
import authentication.auth as auth
from repositories.database import get_db
from services.tag_service import TagService
from helpers.pagination import PaginationSkip, PaginationLimit

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=List[schemas.Tag])
def get_all_tags(
    skip: PaginationSkip = 0,
    limit: PaginationLimit = 100,
    db: Session = Depends(get_db),
):
    """
    Get all tags with pagination.
    Public endpoint - no authentication required.
    """
    return TagService.get_all_tags(db, skip, limit)


@router.get("/search", response_model=List[schemas.Tag])
def search_tags(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db: Session = Depends(get_db),
):
    """
    Search tags by name (for autocomplete).
    Public endpoint - no authentication required.
    """
    return TagService.search_tags(db, q, limit)


@router.get("/by-name/{name}", response_model=schemas.Tag)
def get_tag_by_name(name: str, db: Session = Depends(get_db)):
    """
    Get a tag by its exact name.
    Public endpoint - no authentication required.

    Domain exceptions are caught by centralized exception handlers.
    """
    return TagService.get_tag_by_name(db, name)


@router.get("/popular", response_model=List[schemas.TagWithCount])
def get_popular_tags(
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    min_ideas: int = Query(1, ge=1, description="Minimum ideas per tag"),
    db: Session = Depends(get_db),
):
    """
    Get most popular tags based on number of approved ideas.
    Public endpoint - no authentication required.
    """
    return TagService.get_popular_tags(db, limit, min_ideas)


@router.get("/{tag_id}", response_model=schemas.Tag)
def get_tag_by_id(tag_id: int, db: Session = Depends(get_db)):
    """
    Get a tag by ID.
    Public endpoint - no authentication required.

    Domain exceptions are caught by centralized exception handlers.
    """
    return TagService.get_tag_by_id(db, tag_id)


@router.get("/{tag_id}/statistics", response_model=schemas.TagStatistics)
def get_tag_statistics(tag_id: int, db: Session = Depends(get_db)):
    """
    Get statistics for a tag.
    Public endpoint - no authentication required.

    Domain exceptions are caught by centralized exception handlers.
    """
    return TagService.get_tag_statistics(db, tag_id)


@router.get("/{tag_id}/ideas", response_model=List[int])
def get_ideas_by_tag(
    tag_id: int,
    skip: PaginationSkip = 0,
    limit: PaginationLimit = 20,
    db: Session = Depends(get_db),
):
    """
    Get idea IDs for a specific tag (approved ideas only).
    Public endpoint - no authentication required.

    Returns a list of idea IDs that can be used to fetch full idea details.
    Domain exceptions are caught by centralized exception handlers.
    """
    return TagService.get_ideas_by_tag(
        db=db,
        tag_id=tag_id,
        status_filter=db_models.IdeaStatus.APPROVED,
        skip=skip,
        limit=limit,
    )


@router.get("/{tag_id}/ideas/full", response_model=List[schemas.IdeaWithScore])
def get_ideas_by_tag_full(
    tag_id: int,
    skip: PaginationSkip = 0,
    limit: PaginationLimit = 20,
    db: Session = Depends(get_db),
):
    """
    Get full ideas with scores for a specific tag (approved ideas only).
    Public endpoint - no authentication required.

    Returns paginated list of ideas with vote counts and scores.
    Domain exceptions are caught by centralized exception handlers.
    """
    return TagService.get_ideas_by_tag_full(
        db=db,
        tag_id=tag_id,
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=schemas.Tag)
def create_tag(
    tag: schemas.TagCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
):
    """
    Create a new tag or return existing one.
    Requires authentication.

    Domain exceptions are caught by centralized exception handlers.
    """
    return TagService.create_tag(db, tag)


@router.delete("/{tag_id}")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """
    Delete a tag (admin only).
    Tag must not be in use by any ideas.

    Domain exceptions are caught by centralized exception handlers.
    """
    TagService.delete_tag(db, tag_id)
    return {"message": "Tag deleted successfully"}


@router.post("/cleanup")
def cleanup_unused_tags(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """
    Delete all unused tags (admin only).
    Cleanup operation to remove tags not associated with any ideas.
    """
    count = TagService.delete_unused_tags(db)
    return {"message": f"Deleted {count} unused tag(s)"}
