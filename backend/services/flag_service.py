"""
Service for content flag business logic.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from models.exceptions import (
    CannotFlagOwnContentException,
    CommentNotFoundException,
    DuplicateFlagException,
    FlagAlreadyReviewedException,
    FlagNotFoundException,
    IdeaNotFoundException,
)
from repositories.comment_repository import CommentRepository
from repositories.db_models import (
    ContentFlag,
    ContentType,
    FlagReason,
    FlagStatus,
)
from repositories.flag_repository import FlagRepository
from repositories.idea_repository import IdeaRepository

# Auto-hide threshold
FLAG_THRESHOLD = 3


class FlagService:
    """Service for content flag business logic."""

    @staticmethod
    def create_flag(
        db: Session,
        content_type: ContentType,
        content_id: int,
        reporter_id: int,
        reason: FlagReason,
        details: str | None = None,
    ) -> ContentFlag:
        """
        Create a flag on content.

        Args:
            db: Database session
            content_type: Type of content (comment/idea)
            content_id: ID of the content
            reporter_id: ID of the reporting user
            reason: Reason for flag
            details: Optional additional details

        Returns:
            Created flag

        Raises:
            CommentNotFoundException: If comment not found
            IdeaNotFoundException: If idea not found
            CannotFlagOwnContentException: If user tries to flag own content
            DuplicateFlagException: If user already flagged this content
        """
        flag_repo = FlagRepository(db)

        # Verify content exists and get author
        content_author_id = FlagService._get_content_author_id(
            db, content_type, content_id
        )

        # Cannot flag own content
        if content_author_id == reporter_id:
            raise CannotFlagOwnContentException()

        # Check for duplicate flag
        existing_flag = flag_repo.get_by_content_and_reporter(
            content_type, content_id, reporter_id
        )
        if existing_flag:
            raise DuplicateFlagException()

        # Create the flag
        flag = ContentFlag(
            content_type=content_type,
            content_id=content_id,
            reporter_id=reporter_id,
            reason=reason,
            details=details,
            status=FlagStatus.PENDING,
        )
        created_flag = flag_repo.create(flag)

        # Update content flag count and check threshold
        FlagService._update_content_flag_count(db, content_type, content_id)

        # Update content author's total flags received
        FlagService._increment_author_flags(db, content_author_id)

        return created_flag

    @staticmethod
    def retract_flag(
        db: Session,
        flag_id: int,
        user_id: int,
    ) -> None:
        """
        Retract a flag (only if not yet reviewed).

        Args:
            db: Database session
            flag_id: ID of the flag
            user_id: ID of the user (must be reporter)

        Raises:
            FlagNotFoundException: If flag not found or not owned by user
            FlagAlreadyReviewedException: If flag was already reviewed
        """
        flag_repo = FlagRepository(db)

        flag = flag_repo.get_by_id(flag_id)
        if not flag or flag.reporter_id != user_id:
            raise FlagNotFoundException(flag_id)

        if flag.status != FlagStatus.PENDING:
            raise FlagAlreadyReviewedException()

        # Get content info before deleting flag
        content_type = flag.content_type
        content_id = flag.content_id

        # Delete the flag
        flag_repo.delete_flag(flag)

        # Update content flag count (may un-hide content)
        FlagService._update_content_flag_count(db, content_type, content_id)

    @staticmethod
    def get_user_flags(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ContentFlag]:
        """
        Get flags submitted by a user.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of flags
        """
        flag_repo = FlagRepository(db)
        return flag_repo.get_user_submitted_flags(user_id, skip, limit)

    @staticmethod
    def get_flags_for_content(
        db: Session,
        content_type: ContentType,
        content_id: int,
        include_reviewed: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get all flags for content with reporter info.

        Args:
            db: Database session
            content_type: Type of content
            content_id: ID of content
            include_reviewed: Include reviewed flags

        Returns:
            List of flag dicts with reporter info
        """
        flag_repo = FlagRepository(db)
        flags_with_reporters = flag_repo.get_flags_for_content(
            content_type, content_id, include_reviewed
        )

        return [
            {
                "id": flag.id,
                "content_type": flag.content_type,
                "content_id": flag.content_id,
                "reporter_id": flag.reporter_id,
                "reporter_username": username,
                "reporter_display_name": display_name,
                "reason": flag.reason,
                "details": flag.details,
                "status": flag.status,
                "created_at": flag.created_at,
                "reviewed_at": flag.reviewed_at,
                "review_notes": flag.review_notes,
            }
            for flag, username, display_name in flags_with_reporters
        ]

    @staticmethod
    def _get_content_author_id(
        db: Session,
        content_type: ContentType,
        content_id: int,
    ) -> int:
        """
        Get the author ID of the content.

        Args:
            db: Database session
            content_type: Type of content
            content_id: ID of content

        Returns:
            Author user ID

        Raises:
            CommentNotFoundException: If comment not found
            IdeaNotFoundException: If idea not found
        """
        if content_type == ContentType.COMMENT:
            comment_repo = CommentRepository(db)
            comment = comment_repo.get_by_id(content_id)
            if not comment:
                raise CommentNotFoundException(
                    f"Comment with ID {content_id} not found"
                )
            return int(comment.user_id)  # type: ignore[return-value]
        else:
            idea_repo = IdeaRepository(db)
            idea = idea_repo.get_by_id(content_id)
            if not idea:
                raise IdeaNotFoundException(f"Idea with ID {content_id} not found")
            return int(idea.user_id)  # type: ignore[return-value]

    @staticmethod
    def _update_content_flag_count(
        db: Session,
        content_type: ContentType,
        content_id: int,
    ) -> None:
        """
        Update flag count on content and auto-hide if threshold reached.

        Args:
            db: Database session
            content_type: Type of content
            content_id: ID of content
        """
        flag_repo = FlagRepository(db)
        flag_count = flag_repo.get_pending_flags_count_for_content(
            content_type, content_id
        )

        now = datetime.now(timezone.utc)

        if content_type == ContentType.COMMENT:
            from repositories.comment_repository import CommentRepository

            comment_repo = CommentRepository(db)
            comment = comment_repo.get_by_id(content_id)
            if comment:
                comment.flag_count = flag_count  # type: ignore[assignment]
                if flag_count >= FLAG_THRESHOLD and not comment.is_hidden:
                    comment.is_hidden = True  # type: ignore[assignment]
                    comment.hidden_at = now  # type: ignore[assignment]
                elif flag_count < FLAG_THRESHOLD and comment.is_hidden:
                    # Un-hide if flags were retracted
                    comment.is_hidden = False  # type: ignore[assignment]
                    comment.hidden_at = None  # type: ignore[assignment]
                comment_repo.commit()
        else:
            from repositories.idea_repository import IdeaRepository

            idea_repo = IdeaRepository(db)
            idea = idea_repo.get_by_id(content_id)
            if idea:
                idea.flag_count = flag_count  # type: ignore[assignment]
                if flag_count >= FLAG_THRESHOLD and not idea.is_hidden:
                    idea.is_hidden = True  # type: ignore[assignment]
                    idea.hidden_at = now  # type: ignore[assignment]
                elif flag_count < FLAG_THRESHOLD and idea.is_hidden:
                    idea.is_hidden = False  # type: ignore[assignment]
                    idea.hidden_at = None  # type: ignore[assignment]
                idea_repo.commit()

    @staticmethod
    def _increment_author_flags(db: Session, author_id: int) -> None:
        """
        Increment the total flags received count for a user.

        Args:
            db: Database session
            author_id: ID of the content author
        """
        from repositories.user_repository import UserRepository

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(author_id)
        if user:
            user.total_flags_received = (  # type: ignore[assignment]
                user.total_flags_received or 0
            ) + 1
            user_repo.commit()

    @staticmethod
    def check_user_already_flagged(
        db: Session,
        content_type: ContentType,
        content_id: int,
        user_id: int,
    ) -> bool:
        """
        Check if user has already flagged this content.

        Args:
            db: Database session
            content_type: Type of content
            content_id: ID of content
            user_id: ID of user

        Returns:
            True if already flagged, False otherwise
        """
        flag_repo = FlagRepository(db)
        existing = flag_repo.get_by_content_and_reporter(
            content_type, content_id, user_id
        )
        return existing is not None
