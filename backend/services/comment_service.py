"""
Comment service for business logic.
"""

from typing import List

from sqlalchemy.orm import Session

import models.schemas as schemas
import repositories.db_models as db_models
from models.exceptions import (
    BusinessRuleException,
    CommentNotFoundException,
    IdeaNotFoundException,
    InsufficientPermissionsException,
)
from repositories.comment_repository import CommentRepository, CommentSortOrder
from repositories.idea_repository import IdeaRepository


class CommentService:
    """Service for comment-related business logic."""

    @staticmethod
    def get_comments_for_idea(
        db: Session,
        idea_id: int,
        skip: int = 0,
        limit: int = 50,
        current_user_id: int | None = None,
        sort_by: CommentSortOrder = CommentSortOrder.RELEVANCE,
    ) -> List[schemas.Comment]:
        """
        Get comments for an idea.

        Args:
            db: Database session
            idea_id: Idea ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            current_user_id: Current user ID (for like status), None if not logged in
            sort_by: Sorting order (relevance, newest, oldest, most_liked)

        Returns:
            List of comments with author information and like status

        Raises:
            IdeaNotFoundException: If idea not found
            BusinessRuleException: If idea is not approved
        """
        from services.comment_like_service import CommentLikeService

        # Initialize repositories
        idea_repo = IdeaRepository(db)
        comment_repo = CommentRepository(db)

        # Verify idea exists and is approved
        idea = idea_repo.get_by_id(idea_id)
        if not idea:
            raise IdeaNotFoundException(f"Idea with ID {idea_id} not found")

        if idea.status != db_models.IdeaStatus.APPROVED:
            raise BusinessRuleException("Can only view comments on approved ideas")

        # Get non-moderated comments with sorting
        comments = comment_repo.get_comments_for_idea(
            idea_id, include_moderated=False, skip=skip, limit=limit, sort_by=sort_by
        )

        # Batch load like status if user is authenticated
        comment_ids = [comment.id for comment, _, _ in comments]
        like_status = CommentLikeService.get_user_liked_status(
            db, comment_ids, current_user_id
        )

        # Format results
        result = []
        for comment, username, display_name in comments:
            user_has_liked = (
                like_status.get(comment.id, False)
                if current_user_id is not None
                else None
            )
            comment_dict = {
                "id": comment.id,
                "idea_id": comment.idea_id,
                "user_id": comment.user_id,
                "content": comment.content,
                "is_moderated": comment.is_moderated,
                "created_at": comment.created_at,
                "author_username": username,
                "author_display_name": display_name,
                "like_count": comment.like_count,
                "user_has_liked": user_has_liked,
            }
            result.append(schemas.Comment(**comment_dict))

        return result

    @staticmethod
    def create_comment(
        db: Session,
        idea_id: int,
        user_id: int,
        content: str,
        username: str,
        display_name: str,
        language: str = "fr",
    ) -> tuple[schemas.Comment, bool]:
        """
        Create a new comment on an idea.

        Args:
            db: Database session
            idea_id: Idea ID
            user_id: User ID
            content: Comment content
            username: Username (for response)
            display_name: Display name (for response)
            language: Comment language code (fr or en)

        Returns:
            Tuple of (created comment, requires_approval flag)

        Raises:
            IdeaNotFoundException: If idea not found
            BusinessRuleException: If idea is not approved
        """
        # Initialize repositories
        idea_repo = IdeaRepository(db)
        comment_repo = CommentRepository(db)

        # Verify idea exists and is approved
        idea = idea_repo.get_by_id(idea_id)
        if not idea:
            raise IdeaNotFoundException(f"Idea with ID {idea_id} not found")

        if idea.status != db_models.IdeaStatus.APPROVED:
            raise BusinessRuleException("Can only comment on approved ideas")

        # Check if comment requires approval (inline import to avoid circular deps)
        from repositories.user_repository import UserRepository
        from services.trust_score_service import TrustScoreService

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        requires_approval = (
            TrustScoreService.requires_comment_approval(db, user) if user else True
        )

        # Create comment with language tracking
        db_comment = db_models.Comment(
            idea_id=idea_id,
            user_id=user_id,
            content=content,
            is_moderated=requires_approval,  # Hidden if requires approval
            requires_approval=requires_approval,
            language=language,
        )
        created_comment = comment_repo.create(db_comment)

        # Check content against keyword watchlist
        from repositories.db_models import ContentType
        from services.watchlist_service import WatchlistService

        WatchlistService.check_content_for_keywords(
            db=db,
            content=content,
            content_type=ContentType.COMMENT,
            content_id=int(created_comment.id),  # type: ignore[arg-type]
        )

        # Notify admins if comment requires moderation (fire-and-forget)
        if requires_approval:
            from services.notification_service import NotificationService

            idea_title = str(idea.title) if idea else f"Idea #{idea_id}"
            NotificationService.notify_new_comment(
                comment_id=int(created_comment.id),  # type: ignore[arg-type]
                idea_title=idea_title,
                author_display_name=display_name,
            )

        # Return with user info
        comment = schemas.Comment(
            id=int(created_comment.id),  # type: ignore[arg-type]
            idea_id=int(created_comment.idea_id),  # type: ignore[arg-type]
            user_id=int(created_comment.user_id),  # type: ignore[arg-type]
            content=str(created_comment.content),  # type: ignore[arg-type]
            is_moderated=bool(created_comment.is_moderated),  # type: ignore[arg-type]
            created_at=created_comment.created_at,  # type: ignore[arg-type]
            author_username=username,
            author_display_name=display_name,
        )
        return comment, requires_approval

    @staticmethod
    def delete_comment(db: Session, comment_id: int, user_id: int) -> None:
        """
        Delete a comment.

        Args:
            db: Database session
            comment_id: Comment ID
            user_id: User ID (must be comment author)

        Raises:
            CommentNotFoundException: If comment not found
            InsufficientPermissionsException: If user is not comment author
        """
        comment_repo = CommentRepository(db)

        # Get comment
        comment = comment_repo.get_by_id(comment_id)
        if not comment:
            raise CommentNotFoundException(f"Comment with ID {comment_id} not found")

        # Only the author can delete their comment
        if int(comment.user_id) != user_id:  # type: ignore[arg-type]
            raise InsufficientPermissionsException(
                "Not authorized to delete this comment"
            )

        comment_repo.delete(comment)

    @staticmethod
    def get_all_comments(
        db: Session, skip: int = 0, limit: int = 50
    ) -> List[schemas.Comment]:
        """
        Get all comments for admin (includes moderated).

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of comments with author information
        """
        comment_repo = CommentRepository(db)

        # Get all comments (including moderated)
        comments = comment_repo.get_all_comments(skip=skip, limit=limit)

        # Format results
        result = []
        for comment, username, display_name in comments:
            comment_dict = {
                "id": comment.id,
                "idea_id": comment.idea_id,
                "user_id": comment.user_id,
                "content": comment.content,
                "is_moderated": comment.is_moderated,
                "created_at": comment.created_at,
                "author_username": username,
                "author_display_name": display_name,
            }
            result.append(schemas.Comment(**comment_dict))

        return result

    @staticmethod
    def moderate_comment(
        db: Session, comment_id: int, is_moderated: bool
    ) -> db_models.Comment:
        """
        Moderate a comment (admin function).

        Args:
            db: Database session
            comment_id: Comment ID
            is_moderated: Moderation status

        Returns:
            Updated comment

        Raises:
            CommentNotFoundException: If comment not found
        """
        comment_repo = CommentRepository(db)

        comment = comment_repo.moderate_comment(comment_id, is_moderated)
        if not comment:
            raise CommentNotFoundException(f"Comment with ID {comment_id} not found")

        return comment

    @staticmethod
    def approve_comment(
        db: Session,
        comment_id: int,
        approved_by: int,
    ) -> db_models.Comment:
        """
        Approve a pending comment.

        Args:
            db: Database session
            comment_id: ID of comment to approve
            approved_by: ID of approving admin

        Returns:
            Approved comment

        Raises:
            CommentNotFoundException: If comment not found
        """
        from datetime import datetime, timezone

        from services.trust_score_service import TrustScoreService

        comment_repo = CommentRepository(db)

        comment = comment_repo.get_by_id(comment_id)
        if not comment:
            raise CommentNotFoundException(f"Comment with ID {comment_id} not found")

        if not comment.requires_approval:
            return comment  # Already approved

        now = datetime.now(timezone.utc)
        comment.is_moderated = False
        comment.requires_approval = False
        comment.approved_at = now
        comment.approved_by = approved_by

        comment_repo.commit()
        comment_repo.refresh(comment)

        # Increment user's approved comments count
        TrustScoreService.increment_approved_comments(db, int(comment.user_id))

        return comment

    @staticmethod
    def get_pending_approval_comments(
        db: Session,
        skip: int = 0,
        limit: int = 50,
    ) -> List[schemas.Comment]:
        """
        Get comments pending approval.

        Args:
            db: Database session
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of comments awaiting approval
        """
        comment_repo = CommentRepository(db)
        comments = comment_repo.get_pending_approval(skip, limit)

        result = []
        for comment, username, display_name in comments:
            comment_dict = {
                "id": comment.id,
                "idea_id": comment.idea_id,
                "user_id": comment.user_id,
                "content": comment.content,
                "is_moderated": comment.is_moderated,
                "created_at": comment.created_at,
                "author_username": username,
                "author_display_name": display_name,
            }
            result.append(schemas.Comment(**comment_dict))

        return result

    @staticmethod
    def admin_delete_comment(
        db: Session,
        comment_id: int,
        admin_id: int,
        reason: str,
    ) -> None:
        """
        Admin delete (soft delete) a comment.

        Args:
            db: Database session
            comment_id: Comment ID
            admin_id: Admin user ID performing deletion
            reason: Reason for deletion (audit trail)

        Raises:
            CommentNotFoundException: If comment not found
        """
        from datetime import datetime, timezone

        comment_repo = CommentRepository(db)
        comment = comment_repo.get_by_id(comment_id)

        if not comment:
            raise CommentNotFoundException(f"Comment with ID {comment_id} not found")

        comment.deleted_at = datetime.now(timezone.utc)
        comment.deleted_by = admin_id
        comment.deletion_reason = reason
        comment_repo.commit()

    @staticmethod
    def restore_comment(db: Session, comment_id: int) -> None:
        """
        Restore a deleted comment.

        Args:
            db: Database session
            comment_id: Comment ID

        Raises:
            CommentNotFoundException: If comment not found
        """
        comment_repo = CommentRepository(db)
        comment = comment_repo.get_by_id(comment_id)

        if not comment:
            raise CommentNotFoundException(f"Comment with ID {comment_id} not found")

        comment.deleted_at = None
        comment.deleted_by = None
        comment.deletion_reason = None
        comment_repo.commit()

    @staticmethod
    def reject_pending_comment(
        db: Session,
        comment_id: int,
        admin_id: int,
        reason: str,
    ) -> None:
        """
        Reject and soft-delete a pending comment.

        Args:
            db: Database session
            comment_id: Comment ID
            admin_id: Admin user ID rejecting
            reason: Reason for rejection

        Raises:
            CommentNotFoundException: If comment not found
        """
        from datetime import datetime, timezone

        comment_repo = CommentRepository(db)
        comment = comment_repo.get_by_id(comment_id)

        if not comment:
            raise CommentNotFoundException(f"Comment with ID {comment_id} not found")

        comment.deleted_at = datetime.now(timezone.utc)
        comment.deleted_by = admin_id
        comment.deletion_reason = f"Rejected during approval: {reason}"
        comment_repo.commit()
