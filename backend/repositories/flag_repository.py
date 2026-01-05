"""
Repository for content flag operations.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from repositories.base import BaseRepository
from repositories.db_models import (
    ContentFlag,
    ContentType,
    FlagReason,
    FlagStatus,
    User,
)


class FlagRepository(BaseRepository[ContentFlag]):
    """Repository for content flag data access."""

    def __init__(self, db: Session):
        """
        Initialize flag repository.

        Args:
            db: Database session
        """
        super().__init__(ContentFlag, db)

    def get_by_content_and_reporter(
        self,
        content_type: ContentType,
        content_id: int,
        reporter_id: int,
    ) -> ContentFlag | None:
        """
        Check if user already flagged this content.

        Args:
            content_type: Type of content (comment/idea)
            content_id: ID of the content
            reporter_id: ID of the reporting user

        Returns:
            Existing flag if found, None otherwise
        """
        return (
            self.db.query(ContentFlag)
            .filter(
                ContentFlag.content_type == content_type,
                ContentFlag.content_id == content_id,
                ContentFlag.reporter_id == reporter_id,
            )
            .first()
        )

    def get_flags_for_content(
        self,
        content_type: ContentType,
        content_id: int,
        include_reviewed: bool = False,
    ) -> list[Any]:
        """
        Get all flags for specific content with reporter info.

        Args:
            content_type: Type of content
            content_id: ID of the content
            include_reviewed: Include dismissed/actioned flags

        Returns:
            List of (flag, reporter_username, reporter_display_name)
        """
        query = (
            self.db.query(ContentFlag, User.username, User.display_name)
            .join(User, ContentFlag.reporter_id == User.id)
            .filter(
                ContentFlag.content_type == content_type,
                ContentFlag.content_id == content_id,
            )
        )

        if not include_reviewed:
            query = query.filter(ContentFlag.status == FlagStatus.PENDING)

        return query.order_by(ContentFlag.created_at.desc()).all()

    def get_pending_flags_count_for_content(
        self,
        content_type: ContentType,
        content_id: int,
    ) -> int:
        """
        Get count of pending flags for content.

        Args:
            content_type: Type of content
            content_id: ID of the content

        Returns:
            Number of pending flags
        """
        return (
            self.db.query(func.count(ContentFlag.id))
            .filter(
                ContentFlag.content_type == content_type,
                ContentFlag.content_id == content_id,
                ContentFlag.status == FlagStatus.PENDING,
            )
            .scalar()
            or 0
        )

    def get_user_submitted_flags(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ContentFlag]:
        """
        Get flags submitted by a user.

        Args:
            user_id: ID of the reporter
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of flags
        """
        return (
            self.db.query(ContentFlag)
            .filter(ContentFlag.reporter_id == user_id)
            .order_by(ContentFlag.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_pending_flags_queue(
        self,
        content_type: ContentType | None = None,
        reason: FlagReason | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Any], int]:
        """
        Get unique content items with pending flags for moderation queue.

        Returns content grouped by (content_type, content_id) with flag count.

        Args:
            content_type: Filter by content type
            reason: Filter by flag reason
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (list of (content_type, content_id, flag_count), total_count)
        """
        query = (
            self.db.query(
                ContentFlag.content_type,
                ContentFlag.content_id,
                func.count(ContentFlag.id).label("flag_count"),
            )
            .filter(ContentFlag.status == FlagStatus.PENDING)
            .group_by(ContentFlag.content_type, ContentFlag.content_id)
        )

        if content_type:
            query = query.filter(ContentFlag.content_type == content_type)

        if reason:
            query = query.filter(ContentFlag.reason == reason)

        # Get total count
        total = query.count()

        # Get paginated results ordered by flag count descending
        results = (
            query.order_by(func.count(ContentFlag.id).desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return results, total

    def update_flags_status(
        self,
        flag_ids: list[int],
        status: FlagStatus,
        reviewer_id: int,
        review_notes: str | None = None,
    ) -> int:
        """
        Bulk update flag status.

        Args:
            flag_ids: List of flag IDs to update
            status: New status
            reviewer_id: ID of reviewing admin
            review_notes: Optional notes

        Returns:
            Number of flags updated
        """
        now = datetime.now(timezone.utc)
        result = (
            self.db.query(ContentFlag)
            .filter(ContentFlag.id.in_(flag_ids))
            .update(
                {
                    ContentFlag.status: status,
                    ContentFlag.reviewed_at: now,
                    ContentFlag.reviewed_by: reviewer_id,
                    ContentFlag.review_notes: review_notes,
                },
                synchronize_session=False,
            )
        )
        self.db.commit()
        return result

    def get_flags_by_ids(self, flag_ids: list[int]) -> list[ContentFlag]:
        """
        Get multiple flags by their IDs.

        Args:
            flag_ids: List of flag IDs

        Returns:
            List of flags
        """
        return self.db.query(ContentFlag).filter(ContentFlag.id.in_(flag_ids)).all()

    def count_pending_flags(self) -> int:
        """
        Get total count of pending flags.

        Returns:
            Number of pending flags
        """
        return (
            self.db.query(func.count(ContentFlag.id))
            .filter(ContentFlag.status == FlagStatus.PENDING)
            .scalar()
            or 0
        )

    def count_resolved_today(self) -> int:
        """
        Get count of flags resolved today.

        Returns:
            Number of flags resolved today
        """
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return (
            self.db.query(func.count(ContentFlag.id))
            .filter(
                ContentFlag.status != FlagStatus.PENDING,
                ContentFlag.reviewed_at >= today_start,
            )
            .scalar()
            or 0
        )

    def get_flags_by_reason_stats(self) -> dict[str, int]:
        """
        Get flag counts grouped by reason.

        Returns:
            Dictionary mapping reason to count
        """
        results = (
            self.db.query(ContentFlag.reason, func.count(ContentFlag.id))
            .filter(ContentFlag.status == FlagStatus.PENDING)
            .group_by(ContentFlag.reason)
            .all()
        )
        return {reason.value: count for reason, count in results}

    def delete_flag(self, flag: ContentFlag) -> None:
        """
        Delete a flag (for retracting before review).

        Args:
            flag: Flag to delete
        """
        self.db.delete(flag)
        self.db.commit()

    def get_flagged_users_summary(
        self, skip: int = 0, limit: int = 50
    ) -> tuple[list[Any], int]:
        """
        Get users with pending flagged content for moderation.

        Returns users with their pending flag counts from both comments and ideas.

        Args:
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (list of (User, pending_flags_count), total_count)
        """
        from sqlalchemy import distinct, select, union_all

        from repositories.db_models import Comment, Idea

        # Subquery for flagged comments
        flagged_comments = (
            self.db.query(
                Comment.user_id.label("user_id"),
                func.count(distinct(ContentFlag.id)).label("flag_count"),
            )
            .join(
                ContentFlag,
                (ContentFlag.content_type == ContentType.COMMENT)
                & (ContentFlag.content_id == Comment.id)
                & (ContentFlag.status == FlagStatus.PENDING),
            )
            .group_by(Comment.user_id)
        ).subquery()

        # Subquery for flagged ideas
        flagged_ideas = (
            self.db.query(
                Idea.user_id.label("user_id"),
                func.count(distinct(ContentFlag.id)).label("flag_count"),
            )
            .join(
                ContentFlag,
                (ContentFlag.content_type == ContentType.IDEA)
                & (ContentFlag.content_id == Idea.id)
                & (ContentFlag.status == FlagStatus.PENDING),
            )
            .group_by(Idea.user_id)
        ).subquery()

        # Combine using union_all
        combined = union_all(
            select(
                flagged_comments.c.user_id.label("user_id"),
                flagged_comments.c.flag_count.label("flag_count"),
            ),
            select(
                flagged_ideas.c.user_id.label("user_id"),
                flagged_ideas.c.flag_count.label("flag_count"),
            ),
        ).subquery()

        user_flags = (
            self.db.query(
                combined.c.user_id.label("user_id"),
                func.sum(combined.c.flag_count).label("total_flags"),
            )
            .group_by(combined.c.user_id)
            .subquery()
        )

        query = (
            self.db.query(User, user_flags.c.total_flags)
            .join(user_flags, User.id == user_flags.c.user_id)
            .order_by(user_flags.c.total_flags.desc())
        )

        total = query.count()
        results = query.offset(skip).limit(limit).all()

        return results, total

    def count_total_flags(self) -> int:
        """
        Get total count of all flags.

        Returns:
            Total number of flags
        """
        return self.db.query(func.count(ContentFlag.id)).scalar() or 0

    def get_flags_by_day(self, start_date: datetime) -> list:  # type: ignore[type-arg]
        """
        Get flag counts grouped by day.

        Args:
            start_date: Start date for the query

        Returns:
            List of (date, count) tuples
        """
        return (
            self.db.query(
                func.date(ContentFlag.created_at).label("date"),
                func.count(ContentFlag.id).label("count"),
            )
            .filter(ContentFlag.created_at >= start_date)
            .group_by(func.date(ContentFlag.created_at))
            .order_by(func.date(ContentFlag.created_at))
            .all()
        )

    def count_flags_reviewed_by_admin(self, admin_id: int, start_date: datetime) -> int:
        """
        Count flags reviewed by an admin since start_date.

        Args:
            admin_id: Admin user ID
            start_date: Start date for the query

        Returns:
            Number of flags reviewed
        """
        return (
            self.db.query(func.count(ContentFlag.id))
            .filter(
                ContentFlag.reviewed_by == admin_id,
                ContentFlag.reviewed_at >= start_date,
            )
            .scalar()
            or 0
        )

    def count_flags_actioned_by_admin(self, admin_id: int, start_date: datetime) -> int:
        """
        Count flags actioned by an admin since start_date.

        Args:
            admin_id: Admin user ID
            start_date: Start date for the query

        Returns:
            Number of flags actioned
        """
        return (
            self.db.query(func.count(ContentFlag.id))
            .filter(
                ContentFlag.reviewed_by == admin_id,
                ContentFlag.reviewed_at >= start_date,
                ContentFlag.status == FlagStatus.ACTIONED,
            )
            .scalar()
            or 0
        )

    def count_flags_dismissed_by_admin(
        self, admin_id: int, start_date: datetime
    ) -> int:
        """
        Count flags dismissed by an admin since start_date.

        Args:
            admin_id: Admin user ID
            start_date: Start date for the query

        Returns:
            Number of flags dismissed
        """
        return (
            self.db.query(func.count(ContentFlag.id))
            .filter(
                ContentFlag.reviewed_by == admin_id,
                ContentFlag.reviewed_at >= start_date,
                ContentFlag.status == FlagStatus.DISMISSED,
            )
            .scalar()
            or 0
        )
