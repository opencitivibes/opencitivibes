"""
Service for admin moderation operations.
"""

from typing import Optional

from sqlalchemy.orm import Session

from models.exceptions import FlagNotFoundException
from repositories.db_models import (
    ContentType,
    FlagReason,
    PenaltyType,
)
from repositories.flag_repository import FlagRepository
from services.flag_service import FlagService
from services.penalty_service import PenaltyService
from services.trust_score_service import TrustScoreService


class ModerationService:
    """Service for admin moderation operations."""

    @staticmethod
    def get_moderation_queue(
        db: Session,
        content_type: Optional[ContentType] = None,
        reason: Optional[FlagReason] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int, int]:
        """
        Get moderation queue with flagged content.

        Args:
            db: Database session
            content_type: Filter by content type
            reason: Filter by flag reason
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (list of flagged content items, total, pending_count)
        """
        flag_repo = FlagRepository(db)

        # Get unique flagged content
        content_items, total = flag_repo.get_pending_flags_queue(
            content_type, reason, skip, limit
        )

        pending_count = flag_repo.count_pending_flags()

        result = []
        for ct, content_id, flag_count in content_items:
            # Get content details
            content_data = ModerationService._get_content_details(db, ct, content_id)
            if not content_data:
                continue

            # Get flags with reporters
            flags = FlagService.get_flags_for_content(db, ct, content_id)

            item = {
                "content_type": ct,
                "content_id": content_id,
                **content_data,
                "flag_count": flag_count,
                "flags": flags,
            }
            result.append(item)

        return result, total, pending_count

    @staticmethod
    def review_flags(
        db: Session,
        flag_ids: list[int],
        action: str,
        reviewer_id: int,
        review_notes: Optional[str] = None,
        issue_penalty: bool = False,
        penalty_type: Optional[PenaltyType] = None,
        penalty_reason: Optional[str] = None,
    ) -> dict:
        """
        Review flags and take action.

        Args:
            db: Database session
            flag_ids: IDs of flags to review
            action: "dismiss" or "action"
            reviewer_id: ID of reviewing admin
            review_notes: Optional notes
            issue_penalty: Whether to issue penalty to content author
            penalty_type: Type of penalty to issue
            penalty_reason: Reason for penalty

        Returns:
            Summary of actions taken

        Raises:
            FlagNotFoundException: If flags not found
        """
        flag_repo = FlagRepository(db)

        # Get flags
        flags = flag_repo.get_flags_by_ids(flag_ids)
        if not flags:
            raise FlagNotFoundException(flag_ids[0])

        # All flags should be for same content
        content_type = flags[0].content_type
        content_id = flags[0].content_id
        content_author_id = None

        if action == "dismiss":
            # Dismiss flags
            from repositories.db_models import FlagStatus

            flag_repo.update_flags_status(
                flag_ids, FlagStatus.DISMISSED, reviewer_id, review_notes
            )

            # Unhide content
            ModerationService._unhide_content(db, content_type, content_id)

            # Update content author's trust score (give back points)
            content_author_id = ModerationService._get_content_author_id(
                db, content_type, content_id
            )
            if content_author_id:
                TrustScoreService.update_user_trust_score(db, content_author_id)

            return {
                "action": "dismissed",
                "flags_updated": len(flags),
                "content_unhidden": True,
            }

        elif action == "action":
            # Action flags - delete content
            from repositories.db_models import FlagStatus

            flag_repo.update_flags_status(
                flag_ids, FlagStatus.ACTIONED, reviewer_id, review_notes
            )

            # Soft delete content
            content_author_id = ModerationService._delete_content(
                db,
                content_type,
                content_id,
                reviewer_id,
                f"Removed by moderator: {review_notes or 'Content violation'}",
            )

            # Update author's trust score (penalize)
            if content_author_id:
                TrustScoreService.increment_flags_received(
                    db, content_author_id, is_valid=True
                )

            # Update reporters' trust scores (reward)
            reporter_ids = set(flag.reporter_id for flag in flags)
            for reporter_id in reporter_ids:
                TrustScoreService.increment_successful_reports(db, int(reporter_id))

            # Issue penalty if requested
            penalty_issued = None
            if issue_penalty and penalty_type and penalty_reason and content_author_id:
                penalty = PenaltyService.issue_penalty(
                    db=db,
                    user_id=content_author_id,
                    penalty_type=penalty_type,
                    reason=penalty_reason,
                    issued_by=reviewer_id,
                    related_flag_ids=flag_ids,
                )
                penalty_issued = penalty.id

            return {
                "action": "actioned",
                "flags_updated": len(flags),
                "content_deleted": True,
                "penalty_issued": penalty_issued,
            }

        return {"action": "unknown", "flags_updated": 0}

    @staticmethod
    def get_flagged_users(
        db: Session,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """
        Get users with pending flagged content.

        Args:
            db: Database session
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (list of user summaries, total)
        """
        from repositories.penalty_repository import PenaltyRepository

        flag_repo = FlagRepository(db)
        results, total = flag_repo.get_flagged_users_summary(skip, limit)

        # Build response
        penalty_repo = PenaltyRepository(db)

        user_summaries = []
        for user, pending_flags in results:
            active_penalty = penalty_repo.get_active_penalty(int(user.id))
            user_summaries.append(
                {
                    "user_id": user.id,
                    "username": user.username,
                    "display_name": user.display_name,
                    "trust_score": user.trust_score,
                    "total_flags_received": user.total_flags_received,
                    "valid_flags_received": user.valid_flags_received,
                    "pending_flags_count": int(pending_flags),
                    "has_active_penalty": active_penalty is not None,
                    "active_penalty_type": (
                        active_penalty.penalty_type if active_penalty else None
                    ),
                }
            )

        return user_summaries, total

    @staticmethod
    def _get_content_details(
        db: Session,
        content_type: ContentType,
        content_id: int,
    ) -> Optional[dict]:
        """Get content details for queue display."""
        from repositories.comment_repository import CommentRepository
        from repositories.idea_repository import IdeaRepository

        if content_type == ContentType.COMMENT:
            comment_repo = CommentRepository(db)
            result = comment_repo.get_with_author(content_id)
            if not result:
                return None
            comment, user = result
            return {
                "content_text": str(comment.content)[:500],  # Preview
                "content_author_id": comment.user_id,
                "content_author_username": user.username if user else "Unknown",
                "content_created_at": comment.created_at,
                "is_hidden": comment.is_hidden,
                "author_trust_score": user.trust_score if user else 0,
                "author_total_flags": user.total_flags_received if user else 0,
                "idea_id": comment.idea_id,  # Link to parent idea for context
            }
        else:
            idea_repo = IdeaRepository(db)
            result = idea_repo.get_with_author(content_id)
            if not result:
                return None
            idea, user = result
            return {
                "content_text": f"{idea.title}: {str(idea.description)[:400]}",
                "content_author_id": idea.user_id,
                "content_author_username": user.username if user else "Unknown",
                "content_created_at": idea.created_at,
                "is_hidden": idea.is_hidden,
                "author_trust_score": user.trust_score if user else 0,
                "author_total_flags": user.total_flags_received if user else 0,
            }

    @staticmethod
    def _get_content_author_id(
        db: Session,
        content_type: ContentType,
        content_id: int,
    ) -> Optional[int]:
        """Get author ID for content."""
        from repositories.comment_repository import CommentRepository
        from repositories.idea_repository import IdeaRepository

        if content_type == ContentType.COMMENT:
            comment_repo = CommentRepository(db)
            comment = comment_repo.get_by_id(content_id)
            return int(comment.user_id) if comment else None
        else:
            idea_repo = IdeaRepository(db)
            idea = idea_repo.get_by_id(content_id)
            return int(idea.user_id) if idea else None

    @staticmethod
    def _unhide_content(
        db: Session,
        content_type: ContentType,
        content_id: int,
    ) -> None:
        """Unhide content when flags are dismissed."""
        from repositories.comment_repository import CommentRepository
        from repositories.idea_repository import IdeaRepository

        if content_type == ContentType.COMMENT:
            comment_repo = CommentRepository(db)
            comment_repo.unhide(content_id)
        else:
            idea_repo = IdeaRepository(db)
            idea_repo.unhide(content_id)

    @staticmethod
    def _delete_content(
        db: Session,
        content_type: ContentType,
        content_id: int,
        deleted_by: int,
        reason: str,
    ) -> Optional[int]:
        """Soft delete content and return author ID."""
        from repositories.comment_repository import CommentRepository
        from repositories.idea_repository import IdeaRepository

        if content_type == ContentType.COMMENT:
            comment_repo = CommentRepository(db)
            return comment_repo.soft_delete_for_moderation(
                content_id, deleted_by, reason
            )
        else:
            idea_repo = IdeaRepository(db)
            return idea_repo.soft_delete_for_moderation(content_id, deleted_by, reason)
