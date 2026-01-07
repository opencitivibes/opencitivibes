"""
Idea Service

Handles idea management operations including validation and moderation.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

import models.schemas as schemas
import repositories.db_models as db_models
from models.exceptions import (
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)

from .content_validation import ContentValidationService
from .similar_ideas import SimilarIdeasService
from .tag_service import TagService


def escape_like(text: str) -> str:
    """
    Escape special LIKE pattern characters for safe use in SQL LIKE queries.

    Args:
        text: The text to escape

    Returns:
        Escaped text safe for use in LIKE patterns
    """
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class IdeaService:
    """Service for managing ideas with validation and duplicate detection."""

    @staticmethod
    def get_idea_by_id(
        db: Session, idea_id: int, include_deleted: bool = False
    ) -> Optional[db_models.Idea]:
        """
        Get idea by ID.

        Args:
            db: Database session
            idea_id: Idea ID
            include_deleted: Whether to include deleted ideas

        Returns:
            Idea object or None
        """
        from repositories.idea_repository import IdeaRepository

        repo = IdeaRepository(db)
        return repo.get_by_id_with_deleted(idea_id, include_deleted)

    @staticmethod
    def get_idea_with_score(
        db: Session, idea_id: int, current_user_id: Optional[int] = None
    ) -> schemas.IdeaWithScore:
        """
        Get a single idea with scores and vote information.

        Args:
            db: Database session
            idea_id: Idea ID
            current_user_id: Current user ID for permission check and user vote

        Returns:
            Idea with score information

        Raises:
            NotFoundException: If idea not found
            PermissionDeniedException: If idea is not approved and user is not owner
        """
        from repositories.idea_repository import IdeaRepository

        # Get idea from database for permission check
        db_idea = IdeaService.get_idea_by_id(db, idea_id)
        if not db_idea:
            raise NotFoundException("Idea not found")

        # If idea is not approved, only owner can view it
        if db_idea.status != db_models.IdeaStatus.APPROVED:
            if not current_user_id or int(db_idea.user_id) != current_user_id:  # type: ignore[arg-type]
                raise NotFoundException("Idea not found")

        # Use repository to get the specific idea with scores and user vote
        repo = IdeaRepository(db)
        ideas = repo.get_ideas_with_scores(
            status_filter=db_idea.status,
            current_user_id=current_user_id,
            idea_id=idea_id,
            skip=0,
            limit=1,
        )

        if not ideas:
            raise NotFoundException("Idea not found")

        return ideas[0]

    @staticmethod
    def validate_and_create_idea(
        db: Session, idea: schemas.IdeaCreate, user_id: int, language: str = "en"
    ) -> db_models.Idea:
        """
        Validate and create a new idea.

        Args:
            db: Database session
            idea: Idea data
            user_id: User ID
            language: Language code

        Returns:
            Created idea

        Raises:
            NotFoundException: If category not found
            ValidationException: If content validation fails
        """
        from helpers.sanitization import sanitize_html, sanitize_plain_text
        from repositories.category_repository import CategoryRepository

        # Initialize content validator
        content_validator = ContentValidationService()

        # Validate category exists
        category_repo = CategoryRepository(db)
        category = category_repo.get_by_id(idea.category_id)
        if not category:
            raise NotFoundException("Category not found")

        # Sanitize user input to prevent XSS attacks
        sanitized_title = sanitize_plain_text(idea.title)
        sanitized_description = sanitize_html(idea.description)

        # Validate content for offensive words (use sanitized content)
        is_valid, offensive_words, message = content_validator.validate_idea_content(
            sanitized_title or "", sanitized_description or "", language
        )

        if not is_valid:
            raise ValidationException(message)

        # Create the idea with sanitized content
        from repositories.idea_repository import IdeaRepository

        idea_repo = IdeaRepository(db)
        db_idea = db_models.Idea(
            title=sanitized_title,
            description=sanitized_description,
            category_id=idea.category_id,
            user_id=user_id,
            status=db_models.IdeaStatus.PENDING,
            language=idea.language,
        )

        idea_repo.add(db_idea)
        idea_repo.commit()
        idea_repo.refresh(db_idea)

        # Handle tags if provided
        if idea.tags is not None and len(idea.tags) > 0:
            TagService.sync_idea_tags(db, int(db_idea.id), idea.tags)  # type: ignore[arg-type]
            db.refresh(db_idea)

        # Check content against keyword watchlist
        from repositories.db_models import ContentType
        from services.watchlist_service import WatchlistService

        WatchlistService.check_content_for_keywords(
            db=db,
            content=f"{db_idea.title} {db_idea.description}",
            content_type=ContentType.IDEA,
            content_id=int(db_idea.id),  # type: ignore[arg-type]
        )

        # Index the new idea for search
        from services.search import SearchService

        SearchService.reindex_idea(db, int(db_idea.id))  # type: ignore[arg-type]

        # Notify admins of new pending idea (fire-and-forget)
        from repositories.user_repository import UserRepository
        from services.notification_service import NotificationService

        user_repo = UserRepository(db)
        author = user_repo.get_by_id(user_id)
        author_name = author.display_name if author else "Unknown"

        NotificationService.notify_new_idea(
            idea_id=int(db_idea.id),  # type: ignore[arg-type]
            title=str(db_idea.title),
            category_name=str(category.name_en),
            author_display_name=str(author_name),
        )

        return db_idea

    @staticmethod
    def get_similar_ideas(
        db: Session,
        title: str,
        description: str,
        category_id: Optional[int] = None,
        threshold: float = 0.3,
        limit: int = 5,
        language: str = "en",
    ) -> List[Dict]:
        """
        Find similar approved ideas.

        Args:
            db: Database session
            title: Idea title
            description: Idea description
            category_id: Optional category filter
            threshold: Similarity threshold (0.0 to 1.0)
            limit: Maximum results
            language: Language code

        Returns:
            List of similar ideas with similarity scores
        """
        # Initialize similarity detector
        similarity_detector = SimilarIdeasService()

        return similarity_detector.find_similar_ideas(
            title, description, db, category_id, threshold, limit, language
        )

    # Constants for edit rate limiting
    MAX_EDITS_PER_MONTH = 3
    EDIT_COOLDOWN_HOURS = 24

    @staticmethod
    def update_idea(
        db: Session, idea_id: int, idea_update: schemas.IdeaUpdate, user_id: int
    ) -> db_models.Idea:
        """
        Update an idea (only by owner).

        Supports editing:
        - PENDING ideas: direct edit, resets to PENDING
        - REJECTED ideas: direct edit, resets to PENDING
        - APPROVED ideas: edit with re-moderation (rate limited)

        For APPROVED ideas:
        - Max 3 edits per month per idea
        - 24-hour cool-down between edits
        - Transitions to PENDING_EDIT status
        - Votes and comments are preserved but hidden until re-approved

        Args:
            db: Database session
            idea_id: Idea ID
            idea_update: Updated idea data
            user_id: User ID (must be owner)

        Returns:
            Updated idea

        Raises:
            NotFoundException: If idea not found
            PermissionDeniedException: If user is not owner
            EditRateLimitException: If max edits per month exceeded
            EditCooldownException: If cool-down period not passed
            CannotEditIdeaException: If idea in PENDING_EDIT status
        """
        from models.exceptions import (
            CannotEditIdeaException,
            EditCooldownException,
            EditRateLimitException,
        )
        from repositories.idea_repository import IdeaRepository

        db_idea = IdeaService.get_idea_by_id(db, idea_id)
        if not db_idea:
            raise NotFoundException("Idea not found")

        # Check ownership
        if int(db_idea.user_id) != user_id:  # type: ignore[arg-type]
            raise PermissionDeniedException("You can only edit your own ideas")

        idea_repo = IdeaRepository(db)

        # Handle based on current status
        is_approved_edit = db_idea.status == db_models.IdeaStatus.APPROVED

        # Cannot edit ideas already in PENDING_EDIT (wait for moderation)
        if db_idea.status == db_models.IdeaStatus.PENDING_EDIT:
            raise CannotEditIdeaException(
                "This idea is pending re-moderation. Please wait for admin review."
            )

        # For approved ideas, check rate limiting and cool-down
        if is_approved_edit:
            # Check rate limit (max 3 edits/month)
            edits_this_month = idea_repo.get_edit_count_this_month(idea_id)
            if edits_this_month >= IdeaService.MAX_EDITS_PER_MONTH:
                raise EditRateLimitException(
                    edits_this_month=edits_this_month,
                    max_edits=IdeaService.MAX_EDITS_PER_MONTH,
                )

            # Check cool-down (24 hours between edits)
            if db_idea.last_edit_at is not None:
                from datetime import timedelta

                last_edit = db_idea.last_edit_at
                if hasattr(last_edit, "tzinfo") and last_edit.tzinfo is None:
                    last_edit = last_edit.replace(tzinfo=timezone.utc)

                cooldown_end = last_edit + timedelta(
                    hours=IdeaService.EDIT_COOLDOWN_HOURS
                )
                now = datetime.now(timezone.utc)

                if now < cooldown_end:
                    remaining_hours = (cooldown_end - now).total_seconds() / 3600
                    raise EditCooldownException(
                        message=f"You must wait {remaining_hours:.1f} hours before editing again.",
                        retry_after_hours=remaining_hours,
                    )

        from helpers.sanitization import sanitize_html, sanitize_plain_text

        # Update only provided fields
        update_data = idea_update.model_dump(exclude_unset=True)

        # Extract tags for separate handling
        tags = update_data.pop("tags", None)

        # Sanitize user input to prevent XSS attacks
        if "title" in update_data:
            update_data["title"] = sanitize_plain_text(update_data["title"])
        if "description" in update_data:
            update_data["description"] = sanitize_html(update_data["description"])

        # Validate category if changed
        if "category_id" in update_data:
            from repositories.category_repository import CategoryRepository

            category_repo = CategoryRepository(db)
            category = category_repo.get_by_id(update_data["category_id"])
            if not category:
                raise NotFoundException("Category not found")

        # Apply content updates
        for field, value in update_data.items():
            setattr(db_idea, field, value)

        # Handle status transitions based on previous status
        if is_approved_edit:
            # Approved idea: transition to PENDING_EDIT with tracking
            idea_repo.update_edit_tracking(db_idea, "approved")
        elif db_idea.status == db_models.IdeaStatus.REJECTED:
            # Reset rejected to pending
            db_idea.status = db_models.IdeaStatus.PENDING  # type: ignore[assignment]
            db_idea.admin_comment = None  # type: ignore[assignment]
            idea_repo.commit()
            idea_repo.refresh(db_idea)
        else:
            # PENDING status: just save
            idea_repo.commit()
            idea_repo.refresh(db_idea)

        # Update tags if provided
        if tags is not None:
            TagService.sync_idea_tags(db, int(db_idea.id), tags)  # type: ignore[arg-type]
            db.refresh(db_idea)

        # Reindex for search after update
        from services.search import SearchService

        SearchService.reindex_idea(db, int(db_idea.id))  # type: ignore[arg-type]

        return db_idea

    @staticmethod
    def delete_idea(db: Session, idea_id: int, user_id: int) -> bool:
        """
        Delete (soft-delete) an idea as a normal user.

        Returns True on success. Raises PermissionDeniedException if user
        is not the owner, or NotFoundException if idea does not exist.
        """
        from models.exceptions import PermissionDeniedException
        from models.exceptions import CannotDeleteOthersIdeaException

        try:
            IdeaService.soft_delete_idea(db=db, idea_id=idea_id, user_id=user_id)
            return True
        except CannotDeleteOthersIdeaException:
            # Normalize to PermissionDeniedException for callers
            raise PermissionDeniedException("You can only delete your own ideas")

    @staticmethod
    def soft_delete_idea(
        db: Session,
        idea_id: int,
        user_id: int,
        reason: Optional[str] = None,
        is_admin: bool = False,
    ) -> db_models.Idea:
        """
        Soft delete an idea.

        Args:
            db: Database session
            idea_id: Idea ID
            user_id: ID of user performing the deletion
            reason: Optional reason for deletion
            is_admin: Whether user is an admin

        Returns:
            The deleted idea

        Raises:
            NotFoundException: If idea not found
            IdeaAlreadyDeletedException: If idea is already deleted
            CannotDeleteOthersIdeaException: If non-admin tries to delete other's idea
        """
        from models.exceptions import (
            CannotDeleteOthersIdeaException,
            IdeaAlreadyDeletedException,
        )
        from repositories.idea_repository import IdeaRepository

        repo = IdeaRepository(db)
        db_idea = repo.get_by_id_with_deleted(idea_id, include_deleted=True)

        if not db_idea:
            raise NotFoundException("Idea not found")

        if db_idea.deleted_at is not None:
            raise IdeaAlreadyDeletedException(idea_id)

        # Check ownership for non-admin users
        if not is_admin and int(db_idea.user_id) != user_id:  # type: ignore[arg-type]
            raise CannotDeleteOthersIdeaException()

        # Remove from search index before soft delete
        from services.search import SearchService

        SearchService.remove_idea_from_index(db, idea_id)

        # Perform soft delete
        return repo.soft_delete(db_idea, user_id, reason)

    @staticmethod
    def restore_idea(db: Session, idea_id: int) -> db_models.Idea:
        """
        Restore a soft-deleted idea (admin only).

        Args:
            db: Database session
            idea_id: ID of the idea to restore

        Returns:
            The restored idea

        Raises:
            NotFoundException: If idea doesn't exist
            IdeaNotDeletedException: If idea is not deleted
        """
        from models.exceptions import IdeaNotDeletedException
        from repositories.idea_repository import IdeaRepository

        repo = IdeaRepository(db)
        db_idea = repo.get_deleted_by_id(idea_id)

        if not db_idea:
            # Check if idea exists but isn't deleted
            existing = repo.get_by_id_with_deleted(idea_id, include_deleted=True)
            if existing:
                raise IdeaNotDeletedException(idea_id)
            raise NotFoundException("Idea not found")

        restored_idea = repo.restore(db_idea)

        # Re-add to search index after restore
        from services.search import SearchService

        SearchService.reindex_idea(db, idea_id)

        return restored_idea

    @staticmethod
    def get_deleted_ideas(
        db: Session, skip: int = 0, limit: int = 20
    ) -> tuple[list[db_models.Idea], int]:
        """
        Get paginated list of deleted ideas (admin only).

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (ideas, total_count)
        """
        from repositories.idea_repository import IdeaRepository

        repo = IdeaRepository(db)
        return repo.get_deleted_ideas(skip, limit)

    @staticmethod
    def get_rejected_ideas(
        db: Session, skip: int = 0, limit: int = 20
    ) -> tuple[list[db_models.Idea], int]:
        """
        Get paginated list of rejected ideas (admin only).

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (ideas, total_count)
        """
        from repositories.idea_repository import IdeaRepository

        repo = IdeaRepository(db)
        return repo.get_rejected_ideas(skip, limit)

    @staticmethod
    def moderate_idea(
        db: Session, idea_id: int, moderation: schemas.IdeaModerate
    ) -> db_models.Idea:
        """
        Moderate an idea (approve/reject).

        Handles both new ideas (PENDING) and edited ideas (PENDING_EDIT).
        For PENDING_EDIT ideas:
        - Approval: restores to previous status (typically APPROVED),
          preserves votes/comments
        - Rejection: sets to REJECTED, preserves previous_status for history

        Args:
            db: Database session
            idea_id: Idea ID
            moderation: Moderation data

        Returns:
            Moderated idea

        Raises:
            NotFoundException: If idea not found
        """
        from repositories.idea_repository import IdeaRepository

        db_idea = IdeaService.get_idea_by_id(db, idea_id)
        if not db_idea:
            raise NotFoundException("Idea not found")

        idea_repo = IdeaRepository(db)
        was_pending_edit = db_idea.status == db_models.IdeaStatus.PENDING_EDIT

        if was_pending_edit:
            # Special handling for edited ideas awaiting re-moderation
            if moderation.status == db_models.IdeaStatus.APPROVED:
                # Approve edit: restore to previous status (typically APPROVED)
                # This keeps votes and comments intact
                idea_repo.restore_previous_status(db_idea)
                db_idea.admin_comment = moderation.admin_comment  # type: ignore[assignment]
            else:
                # Reject edit: set to REJECTED
                # Previous_status preserved for history
                db_idea.status = moderation.status  # type: ignore[assignment]
                db_idea.admin_comment = moderation.admin_comment  # type: ignore[assignment]
                idea_repo.commit()
                idea_repo.refresh(db_idea)
        else:
            # Standard moderation for new ideas (PENDING status)
            db_idea.status = moderation.status  # type: ignore[assignment]
            db_idea.admin_comment = moderation.admin_comment  # type: ignore[assignment]

            if moderation.status == db_models.IdeaStatus.APPROVED:
                db_idea.validated_at = datetime.now(timezone.utc)  # type: ignore[assignment]

            idea_repo.commit()
            idea_repo.refresh(db_idea)

        return db_idea

    @staticmethod
    def get_ideas_by_status(
        db: Session,
        status: db_models.IdeaStatus,
        category_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[db_models.Idea]:
        """
        Get ideas by status with optional category filter.

        Args:
            db: Database session
            status: Idea status
            category_id: Optional category filter
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of ideas (excludes deleted)
        """
        from repositories.idea_repository import IdeaRepository

        idea_repo = IdeaRepository(db)
        return idea_repo.get_by_status_filtered(
            status=status,
            category_id=category_id,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_ideas_by_user(
        db: Session, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[db_models.Idea]:
        """
        Get all ideas by a specific user.

        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of ideas (excludes deleted)
        """
        from repositories.idea_repository import IdeaRepository

        idea_repo = IdeaRepository(db)
        return idea_repo.get_by_user_excluding_deleted(
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def merge_ideas(
        db: Session, source_idea_id: int, target_idea_id: int
    ) -> db_models.Idea:
        """
        Merge duplicate ideas by moving votes and comments.

        Args:
            db: Database session
            source_idea_id: Idea to merge from (will be deleted)
            target_idea_id: Idea to merge into

        Returns:
            Target idea with merged data

        Raises:
            NotFoundException: If source or target idea not found
            ValidationException: If trying to merge idea into itself
        """
        from repositories.idea_repository import IdeaRepository
        from repositories.vote_repository import VoteRepository

        source_idea = IdeaService.get_idea_by_id(db, source_idea_id)
        target_idea = IdeaService.get_idea_by_id(db, target_idea_id)

        if not source_idea:
            raise NotFoundException("Source idea not found")
        if not target_idea:
            raise NotFoundException("Target idea not found")

        # Cannot merge same idea
        if source_idea_id == target_idea_id:
            raise ValidationException("Cannot merge idea into itself")

        # Move votes from source to target (avoid duplicate votes per user)
        vote_repo = VoteRepository(db)
        source_votes = vote_repo.get_votes_for_idea(source_idea_id)

        idea_repo = IdeaRepository(db)

        for vote in source_votes:
            # Check if user already voted on target
            existing_vote = vote_repo.get_by_idea_and_user(
                target_idea_id,
                int(vote.user_id),  # type: ignore[arg-type]
            )

            if not existing_vote:
                # Move vote to target
                vote.idea_id = target_idea_id  # type: ignore[assignment]
            else:
                # User already voted on target, delete source vote
                vote_repo.delete(vote)

        # Move comments from source to target
        idea_repo.bulk_update_comments_idea_id(source_idea_id, target_idea_id)

        # Delete source idea
        idea_repo.delete(source_idea)
        idea_repo.refresh(target_idea)

        return target_idea

    @staticmethod
    def search_ideas(
        db: Session,
        query: str,
        category_id: Optional[int] = None,
        status: Optional[db_models.IdeaStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[db_models.Idea]:
        """
        Search ideas by keyword in title or description.

        Args:
            db: Database session
            query: Search query
            category_id: Optional category filter
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of matching ideas
        """
        from repositories.idea_repository import IdeaRepository

        # Escape special LIKE characters to prevent pattern injection
        escaped_query = escape_like(query)

        idea_repo = IdeaRepository(db)
        return idea_repo.search_basic(
            search_term=escaped_query,
            category_id=category_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_idea_statistics(db: Session, idea_id: int) -> schemas.IdeaStatistics:
        """
        Get statistics for an idea.

        Args:
            db: Database session
            idea_id: Idea ID

        Returns:
            IdeaStatistics schema with idea statistics

        Raises:
            NotFoundException: If idea not found
        """
        from repositories.idea_repository import IdeaRepository

        idea = IdeaService.get_idea_by_id(db, idea_id)
        if not idea:
            raise NotFoundException("Idea not found")

        idea_repo = IdeaRepository(db)
        vote_stats = idea_repo.get_vote_statistics(idea_id)
        upvotes = vote_stats["upvotes"]
        downvotes = vote_stats["downvotes"]
        comments = idea_repo.get_comment_count(idea_id)

        return schemas.IdeaStatistics(
            idea_id=idea_id,
            title=str(idea.title),
            status=idea.status.value,
            created_at=idea.created_at,  # type: ignore[arg-type]
            validated_at=idea.validated_at,  # type: ignore[arg-type]
            upvotes=upvotes,
            downvotes=downvotes,
            score=upvotes - downvotes,
            comments=comments,
        )

    @staticmethod
    def get_leaderboard(
        db: Session,
        category_id: Optional[int] = None,
        current_user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
        preferred_language: Optional[str] = None,
    ) -> List[schemas.IdeaWithScore]:
        """
        Get approved ideas for leaderboard.

        Args:
            db: Database session
            category_id: Optional category filter
            current_user_id: Current user ID for user vote info
            skip: Number of records to skip
            limit: Maximum number of records to return
            preferred_language: Optional language code ('fr' or 'en') for
                prioritization. Ideas in the preferred language appear first.

        Returns:
            List of approved ideas with scores
        """
        import sentry_sdk

        from repositories.idea_repository import IdeaRepository

        with sentry_sdk.start_span(
            op="service.leaderboard", description="Get idea leaderboard"
        ) as span:
            span.set_data("category_id", category_id)
            span.set_data("user_id", current_user_id)
            span.set_data("pagination", {"skip": skip, "limit": limit})
            span.set_data("preferred_language", preferred_language)

            repo = IdeaRepository(db)
            ideas = repo.get_ideas_with_scores(
                status_filter=db_models.IdeaStatus.APPROVED,
                category_id=category_id,
                current_user_id=current_user_id,
                skip=skip,
                limit=limit,
                preferred_language=preferred_language,
            )
            span.set_data("ideas_count", len(ideas))
            return ideas

    @staticmethod
    def get_my_ideas(
        db: Session, user_id: int, skip: int = 0, limit: int = 20
    ) -> List[schemas.IdeaWithScore]:
        """
        Get all ideas by a specific user (all statuses) in a single query.

        Orders by status priority (pending first) then by created_at desc.

        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user's ideas with scores
        """
        from repositories.idea_repository import IdeaRepository

        repo = IdeaRepository(db)

        # Single optimized query for all statuses
        return repo.get_user_ideas_all_statuses(
            user_id=user_id,
            current_user_id=user_id,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_pending_ideas_for_admin(
        db: Session, current_user_id: int, skip: int = 0, limit: int = 20
    ) -> List[schemas.IdeaWithScore]:
        """
        Get pending ideas for admin review.

        Args:
            db: Database session
            current_user_id: Admin user ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of pending ideas with scores
        """
        from repositories.idea_repository import IdeaRepository

        repo = IdeaRepository(db)
        return repo.get_ideas_with_scores(
            status_filter=db_models.IdeaStatus.PENDING,
            current_user_id=current_user_id,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_approved_ideas_for_admin(
        db: Session,
        category_id: Optional[int] = None,
        current_user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        quality_key: Optional[str] = None,
        min_quality_count: int = 0,
    ) -> List[schemas.IdeaWithScore]:
        """
        Get approved ideas for admin management with optional quality filtering.

        Args:
            db: Database session
            category_id: Optional category filter
            current_user_id: Admin user ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            quality_key: Optional quality key to filter by
            min_quality_count: Minimum count of this quality required

        Returns:
            List of approved ideas with scores
        """

        from repositories.idea_repository import IdeaRepository
        from repositories.quality_repository import QualityRepository

        repo = IdeaRepository(db)

        # If no quality filter, use the standard method
        if not quality_key or min_quality_count <= 0:
            return repo.get_ideas_with_scores(
                status_filter=db_models.IdeaStatus.APPROVED,
                category_id=category_id,
                current_user_id=current_user_id,
                skip=skip,
                limit=limit,
            )

        # Get quality ID from key
        quality_repo = QualityRepository(db)
        quality = quality_repo.get_by_key(quality_key)
        if not quality:
            return []

        # Get idea IDs that meet quality filter criteria
        idea_ids = repo.get_approved_with_quality_filter(
            quality_id=int(quality.id),
            min_quality_count=min_quality_count,
            category_id=category_id,
            skip=skip,
            limit=limit,
        )

        if not idea_ids:
            return []

        # Get full idea data for these IDs (preserving order)
        ideas = repo.get_ideas_with_scores(
            status_filter=db_models.IdeaStatus.APPROVED,
            current_user_id=current_user_id,
            skip=0,
            limit=len(idea_ids),
        )

        # Filter to only the matching IDs and preserve order
        ideas_map = {idea.id: idea for idea in ideas if idea.id in idea_ids}
        return [ideas_map[id] for id in idea_ids if id in ideas_map]

    @staticmethod
    def get_pending_ideas_for_admin_with_permissions(
        db: Session,
        user: db_models.User,
        skip: int = 0,
        limit: int = 20,
    ) -> List[schemas.IdeaWithScore]:
        """
        Get pending ideas for admin review with permission checking.

        This method handles:
        1. Permission verification (global admin or category admin)
        2. Category filtering for non-global admins

        Args:
            db: Database session
            user: Current admin user
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of pending ideas with scores, filtered by category if needed

        Raises:
            InsufficientPermissionsException: If user has no admin permissions
        """
        from models.exceptions import InsufficientPermissionsException
        from repositories.idea_repository import IdeaRepository
        from services.admin_role_service import AdminRoleService

        # Check if user has any admin permissions
        is_global_admin = bool(user.is_global_admin)

        if not is_global_admin:
            admin_roles = AdminRoleService.get_user_admin_roles(
                db,
                int(user.id),  # type: ignore[arg-type]
            )
            if not admin_roles:
                raise InsufficientPermissionsException("Not enough permissions")

        repo = IdeaRepository(db)
        user_id: int = user.id  # type: ignore[assignment]
        # Include both PENDING and PENDING_EDIT statuses for admin moderation queue
        pending_ideas = repo.get_ideas_with_scores(
            status_filter=[
                db_models.IdeaStatus.PENDING,
                db_models.IdeaStatus.PENDING_EDIT,
            ],
            current_user_id=user_id,
            skip=skip,
            limit=limit,
        )

        # Filter by category if user is category admin (not global admin)
        if not is_global_admin:
            admin_roles = AdminRoleService.get_user_admin_roles(
                db,
                int(user.id),  # type: ignore[arg-type]
            )
            admin_category_ids: list[int] = [
                role.category_id  # type: ignore[misc]
                for role in admin_roles
                if role.category_id is not None  # type: ignore[truthy-bool]
            ]
            pending_ideas = [
                idea for idea in pending_ideas if idea.category_id in admin_category_ids
            ]

        return pending_ideas

    @staticmethod
    def count_pending_ideas_for_admin_with_permissions(
        db: Session,
        user: db_models.User,
    ) -> int:
        """
        Count pending ideas respecting admin permissions.

        Global admins see all pending ideas.
        Category admins see only their assigned categories.

        Args:
            db: Database session
            user: Current admin user

        Returns:
            Total count of pending ideas visible to this admin

        Raises:
            InsufficientPermissionsException: If user has no admin permissions
        """
        from models.exceptions import InsufficientPermissionsException
        from repositories.idea_repository import IdeaRepository
        from services.admin_role_service import AdminRoleService

        is_global_admin = bool(user.is_global_admin)
        repo = IdeaRepository(db)

        # Global admin sees all
        if is_global_admin:
            return repo.count_pending_ideas()

        # Category admin sees only their categories
        admin_roles = AdminRoleService.get_user_admin_roles(
            db,
            int(user.id),  # type: ignore[arg-type]
        )
        if not admin_roles:
            raise InsufficientPermissionsException("Not enough permissions")

        category_ids: list[int] = [
            role.category_id  # type: ignore[misc]
            for role in admin_roles
            if role.category_id is not None  # type: ignore[truthy-bool]
        ]
        return repo.count_pending_ideas(category_ids)

    @staticmethod
    def moderate_idea_with_permissions(
        db: Session,
        user: db_models.User,
        idea_id: int,
        moderation: schemas.IdeaModerate,
    ) -> db_models.Idea:
        """
        Moderate an idea with permission checking.

        Args:
            db: Database session
            user: Current admin user
            idea_id: ID of the idea to moderate
            moderation: Moderation data

        Returns:
            Moderated idea

        Raises:
            NotFoundException: If idea not found
            InsufficientPermissionsException: If user lacks permissions
        """
        from models.exceptions import InsufficientPermissionsException
        from services.admin_role_service import AdminRoleService

        idea = IdeaService.get_idea_by_id(db, idea_id)
        if not idea:
            raise NotFoundException("Idea not found")

        # Check admin permissions for this category
        category_id = (
            int(idea.category_id) if idea.category_id else None  # type: ignore[arg-type]
        )

        if not bool(user.is_global_admin):
            if category_id is None:
                raise InsufficientPermissionsException(
                    "Not enough permissions for this category"
                )

            is_category_admin = AdminRoleService.is_category_admin(
                db,
                int(user.id),
                category_id,  # type: ignore[arg-type]
            )
            if not is_category_admin:
                raise InsufficientPermissionsException(
                    "Not enough permissions for this category"
                )

        return IdeaService.moderate_idea(db, idea_id, moderation)
