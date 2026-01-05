"""
Comment repository for database operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

import repositories.db_models as db_models

from .base import BaseRepository

if TYPE_CHECKING:
    from models.schemas import CommentSortOrder


class CommentRepository(BaseRepository[db_models.Comment]):
    """Repository for Comment entity database operations."""

    def __init__(self, db: Session):
        """
        Initialize comment repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.Comment, db)

    def get_comments_for_idea(
        self,
        idea_id: int,
        include_moderated: bool = False,
        skip: int = 0,
        limit: int = 50,
        sort_by: CommentSortOrder | None = None,
    ) -> list[Any]:
        """
        Get comments for an idea with author information.

        Args:
            idea_id: Idea ID
            include_moderated: Include moderated comments
            skip: Number of records to skip
            limit: Maximum number of records to return
            sort_by: Sorting order (relevance, newest, oldest, most_liked)

        Returns:
            List of tuples (comment, author_username, author_display_name)
        """
        # Import at runtime to avoid circular import
        from models.schemas import CommentSortOrder as SortOrder

        if sort_by is None:
            sort_by = SortOrder.RELEVANCE

        query = (
            self.db.query(
                db_models.Comment,
                db_models.User.username.label("author_username"),
                db_models.User.display_name.label("author_display_name"),
            )
            .join(db_models.User, db_models.Comment.user_id == db_models.User.id)
            .filter(
                db_models.Comment.idea_id == idea_id,
                # Exclude soft-deleted comments
                db_models.Comment.deleted_at.is_(None),
                # Exclude hidden comments (flagged and pending review)
                db_models.Comment.is_hidden == False,  # noqa: E712
            )
        )

        if not include_moderated:
            query = query.filter(db_models.Comment.is_moderated == False)  # noqa: E712

        # Apply sorting based on sort_by parameter
        if sort_by == SortOrder.NEWEST:
            query = query.order_by(db_models.Comment.created_at.desc())
        elif sort_by == SortOrder.OLDEST:
            query = query.order_by(db_models.Comment.created_at.asc())
        elif sort_by == SortOrder.MOST_LIKED:
            query = query.order_by(
                db_models.Comment.like_count.desc(),
                db_models.Comment.created_at.desc(),
            )
        else:  # RELEVANCE - default: combination of likes and recency
            query = query.order_by(
                db_models.Comment.like_count.desc(),
                db_models.Comment.created_at.desc(),
            )

        return query.offset(skip).limit(limit).all()

    def get_by_user(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[db_models.Comment]:
        """
        Get comments by user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of comments
        """
        return (
            self.db.query(db_models.Comment)
            .filter(db_models.Comment.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_comments(self, skip: int = 0, limit: int = 50) -> list[Any]:
        """
        Get all comments (admin function) with author information.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of tuples (comment, author_username, author_display_name)
        """
        return (
            self.db.query(
                db_models.Comment,
                db_models.User.username.label("author_username"),
                db_models.User.display_name.label("author_display_name"),
            )
            .join(db_models.User, db_models.Comment.user_id == db_models.User.id)
            .order_by(db_models.Comment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def moderate_comment(
        self, comment_id: int, is_moderated: bool
    ) -> db_models.Comment | None:
        """
        Moderate a comment.

        Args:
            comment_id: Comment ID
            is_moderated: Moderation status

        Returns:
            Updated comment, or None if not found
        """
        comment = self.get_by_id(comment_id)
        if comment:
            comment.is_moderated = is_moderated  # type: ignore[assignment]
            return self.update(comment)
        return None

    def get_pending_approval(self, skip: int = 0, limit: int = 50) -> list[Any]:
        """
        Get comments pending approval with author information.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of tuples (comment, author_username, author_display_name)
        """
        return (
            self.db.query(
                db_models.Comment,
                db_models.User.username.label("author_username"),
                db_models.User.display_name.label("author_display_name"),
            )
            .join(db_models.User, db_models.Comment.user_id == db_models.User.id)
            .filter(
                db_models.Comment.requires_approval == True,  # noqa: E712
                db_models.Comment.approved_at.is_(None),
                db_models.Comment.deleted_at.is_(None),
            )
            .order_by(db_models.Comment.created_at.asc())  # Oldest first
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_pending_approval(self) -> int:
        """Get count of comments pending approval."""
        from sqlalchemy import func

        result = (
            self.db.query(func.count(db_models.Comment.id))
            .filter(
                db_models.Comment.requires_approval == True,  # noqa: E712
                db_models.Comment.approved_at.is_(None),
                db_models.Comment.deleted_at.is_(None),
            )
            .scalar()
        )
        return result or 0

    def delete_by_user_id(self, user_id: int) -> int:
        """
        Delete all comments by a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted records
        """
        count = (
            self.db.query(db_models.Comment)
            .filter(db_models.Comment.user_id == user_id)
            .delete()
        )
        return count

    def delete_by_idea_id(self, idea_id: int) -> int:
        """
        Delete all comments for an idea.

        Args:
            idea_id: Idea ID

        Returns:
            Number of deleted records
        """
        count = (
            self.db.query(db_models.Comment)
            .filter(db_models.Comment.idea_id == idea_id)
            .delete()
        )
        return count

    def get_with_author(self, comment_id: int) -> Any | None:
        """
        Get comment with its author.

        Args:
            comment_id: Comment ID

        Returns:
            Tuple of (Comment, User) or None if not found
        """
        return (
            self.db.query(db_models.Comment, db_models.User)
            .join(db_models.User, db_models.Comment.user_id == db_models.User.id)
            .filter(db_models.Comment.id == comment_id)
            .first()
        )

    def unhide(self, comment_id: int) -> bool:
        """
        Unhide a comment and reset flag count.

        Args:
            comment_id: Comment ID

        Returns:
            True if updated, False if not found
        """
        comment = self.get_by_id(comment_id)
        if not comment:
            return False

        comment.is_hidden = False  # type: ignore[assignment]
        comment.hidden_at = None  # type: ignore[assignment]
        comment.flag_count = 0  # type: ignore[assignment]
        self.commit()
        return True

    def soft_delete_for_moderation(
        self,
        comment_id: int,
        deleted_by: int,
        reason: str,
    ) -> int | None:
        """
        Soft delete a comment for moderation.

        Args:
            comment_id: Comment ID
            deleted_by: ID of user performing deletion
            reason: Deletion reason

        Returns:
            Author ID if deleted, None if not found
        """
        from datetime import datetime, timezone

        comment = self.get_by_id(comment_id)
        if not comment:
            return None

        author_id = int(comment.user_id)
        comment.deleted_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        comment.deleted_by = deleted_by  # type: ignore[assignment]
        comment.deletion_reason = reason  # type: ignore[assignment]
        self.commit()
        return author_id

    def bulk_soft_delete_by_user(
        self,
        user_id: int,
        deleted_by: int,
        reason: str,
    ) -> int:
        """
        Soft delete all non-deleted comments by a user.

        Used when banning a user.

        Args:
            user_id: User ID whose comments to delete
            deleted_by: ID of admin performing deletion
            reason: Deletion reason

        Returns:
            Number of comments deleted
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        result = (
            self.db.query(db_models.Comment)
            .filter(
                db_models.Comment.user_id == user_id,
                db_models.Comment.deleted_at.is_(None),
            )
            .update(
                {
                    db_models.Comment.deleted_at: now,
                    db_models.Comment.deleted_by: deleted_by,
                    db_models.Comment.deletion_reason: reason,
                },
                synchronize_session=False,
            )
        )
        return result
