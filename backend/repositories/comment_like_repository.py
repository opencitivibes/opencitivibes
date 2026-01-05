"""Repository for comment like operations."""

from sqlalchemy.orm import Session

import repositories.db_models as db_models
from repositories.base import BaseRepository


class CommentLikeRepository(BaseRepository[db_models.CommentLike]):
    """Repository for CommentLike CRUD operations."""

    def __init__(self, db: Session):
        """
        Initialize comment like repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.CommentLike, db)

    def get_by_comment_and_user(
        self, comment_id: int, user_id: int
    ) -> db_models.CommentLike | None:
        """
        Get a like by comment and user IDs.

        Args:
            comment_id: Comment ID
            user_id: User ID

        Returns:
            CommentLike if found, None otherwise
        """
        return (
            self.db.query(db_models.CommentLike)
            .filter(
                db_models.CommentLike.comment_id == comment_id,
                db_models.CommentLike.user_id == user_id,
            )
            .first()
        )

    def get_user_liked_comment_ids(
        self, user_id: int, comment_ids: list[int]
    ) -> set[int]:
        """
        Get set of comment IDs that user has liked (for batch loading).

        Args:
            user_id: User ID
            comment_ids: List of comment IDs to check

        Returns:
            Set of comment IDs that the user has liked
        """
        if not comment_ids:
            return set()
        likes = (
            self.db.query(db_models.CommentLike.comment_id)
            .filter(
                db_models.CommentLike.user_id == user_id,
                db_models.CommentLike.comment_id.in_(comment_ids),
            )
            .all()
        )
        return {like.comment_id for like in likes}

    def count_by_comment(self, comment_id: int) -> int:
        """
        Count likes for a comment.

        Args:
            comment_id: Comment ID

        Returns:
            Number of likes on the comment
        """
        return (
            self.db.query(db_models.CommentLike)
            .filter(db_models.CommentLike.comment_id == comment_id)
            .count()
        )

    def delete_by_comment_and_user(self, comment_id: int, user_id: int) -> bool:
        """
        Delete a like by comment and user.

        Args:
            comment_id: Comment ID
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        like = self.get_by_comment_and_user(comment_id, user_id)
        if not like:
            return False

        self.db.delete(like)
        self.db.commit()
        return True
