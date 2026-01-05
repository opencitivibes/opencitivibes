"""Service for comment like operations."""

from sqlalchemy.orm import Session

from models.exceptions import (
    BusinessRuleException,
    CommentNotFoundException,
)
from repositories.comment_like_repository import CommentLikeRepository
from repositories.comment_repository import CommentRepository
from repositories.db_models import CommentLike


class CommentLikeService:
    """Service for comment like business logic."""

    @staticmethod
    def toggle_like(
        db: Session, comment_id: int, user_id: int
    ) -> dict[str, bool | int]:
        """
        Toggle like on a comment.

        Args:
            db: Database session
            comment_id: Comment ID to like/unlike
            user_id: User performing the action

        Returns:
            Dict with 'liked' (bool) and 'like_count' (int).

        Raises:
            CommentNotFoundException: Comment not found
            BusinessRuleException: Cannot like own comment or hidden/deleted comment
        """
        comment_repo = CommentRepository(db)
        like_repo = CommentLikeRepository(db)

        # Get comment
        comment = comment_repo.get_by_id(comment_id)
        if not comment:
            raise CommentNotFoundException(f"Comment {comment_id} not found")

        # Validate comment is likeable
        if comment.deleted_at is not None:
            raise BusinessRuleException("Cannot like deleted comments")
        if comment.is_hidden:
            raise BusinessRuleException("Cannot like hidden comments")

        # Cannot like own comment
        if comment.user_id == user_id:
            raise BusinessRuleException("Cannot like your own comment")

        # Check existing like
        existing = like_repo.get_by_comment_and_user(comment_id, user_id)

        if existing:
            # Unlike
            like_repo.delete(existing)
            comment.like_count = max(0, comment.like_count - 1)
            liked = False
        else:
            # Like
            new_like = CommentLike(comment_id=comment_id, user_id=user_id)
            like_repo.create(new_like)
            comment.like_count += 1
            liked = True

        comment_repo.commit()
        comment_repo.refresh(comment)

        return {"liked": liked, "like_count": comment.like_count}

    @staticmethod
    def get_user_liked_status(
        db: Session, comment_ids: list[int], user_id: int | None
    ) -> dict[int, bool]:
        """
        Batch get like status for multiple comments.

        Args:
            db: Database session
            comment_ids: List of comment IDs to check
            user_id: User ID to check likes for (None if not authenticated)

        Returns:
            Dict mapping comment_id -> user_has_liked.
            Returns empty dict if user_id is None.
        """
        if user_id is None or not comment_ids:
            return {}

        like_repo = CommentLikeRepository(db)
        liked_ids = like_repo.get_user_liked_comment_ids(user_id, comment_ids)

        return {cid: cid in liked_ids for cid in comment_ids}
