from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from helpers.pagination import PaginationLimitComments, PaginationSkip
from repositories.database import get_db
from services.comment_service import CommentService

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("/{idea_id}", response_model=List[schemas.Comment])
def get_comments_for_idea(
    idea_id: int,
    skip: PaginationSkip = 0,
    limit: PaginationLimitComments = 50,
    sort_by: schemas.CommentSortOrder = schemas.CommentSortOrder.RELEVANCE,
    db: Session = Depends(get_db),
    current_user: db_models.User | None = Depends(auth.get_current_user_optional),
):
    """
    Get comments for an idea with optional sorting.

    Includes user_has_liked field when authenticated.
    Domain exceptions are caught by centralized exception handlers.
    """
    current_user_id = current_user.id if current_user else None
    return CommentService.get_comments_for_idea(
        db=db,
        idea_id=idea_id,
        skip=skip,
        limit=limit,
        current_user_id=current_user_id,
        sort_by=sort_by,
    )


@router.post("/{idea_id}", response_model=schemas.Comment)
def create_comment(
    idea_id: int,
    comment: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
) -> schemas.Comment:
    """
    Create a comment on an idea.

    Returns 202 Accepted if the comment requires approval.
    Domain exceptions are caught by centralized exception handlers.
    """
    from fastapi.responses import JSONResponse

    user_id: int = current_user.id  # type: ignore[assignment]
    username: str = str(current_user.username)  # type: ignore[arg-type]
    display_name: str = str(current_user.display_name)  # type: ignore[arg-type]
    created_comment, requires_approval = CommentService.create_comment(
        db=db,
        idea_id=idea_id,
        user_id=user_id,
        content=comment.content,
        username=username,
        display_name=display_name,
        language=comment.language,
    )

    if requires_approval:
        # Return 202 Accepted for comments pending approval
        return JSONResponse(  # type: ignore[return-value]
            status_code=202,
            content={
                "message": "Comment submitted and pending approval",
                "comment": created_comment.model_dump(mode="json"),
            },
        )

    return created_comment


@router.delete("/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
):
    """
    Delete a comment.

    Domain exceptions are caught by centralized exception handlers.
    """
    user_id: int = current_user.id  # type: ignore[assignment]
    CommentService.delete_comment(db=db, comment_id=comment_id, user_id=user_id)
    return {"message": "Comment deleted successfully"}


@router.post("/{comment_id}/like", response_model=schemas.CommentLikeResponse)
def toggle_comment_like(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_current_active_user),
):
    """
    Toggle like on a comment.

    - If not liked: creates like
    - If already liked: removes like

    Returns new like state and count.
    Domain exceptions are caught by centralized exception handlers.
    """
    from services.comment_like_service import CommentLikeService

    user_id: int = current_user.id  # type: ignore[assignment]
    return CommentLikeService.toggle_like(db, comment_id, user_id)
