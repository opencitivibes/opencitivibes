"""
User repository for database operations.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

import repositories.db_models as db_models
from .base import BaseRepository


class UserRepository(BaseRepository[db_models.User]):
    """Repository for User entity database operations."""

    def __init__(self, db: Session):
        """
        Initialize user repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.User, db)

    def get_by_email(self, email: str) -> Optional[db_models.User]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        return (
            self.db.query(db_models.User).filter(db_models.User.email == email).first()
        )

    def get_active_by_email(self, email: str) -> Optional[db_models.User]:
        """
        Get active user by email.

        Args:
            email: User email

        Returns:
            User if found and active, None otherwise
        """
        return (
            self.db.query(db_models.User)
            .filter(
                db_models.User.email == email,
                db_models.User.is_active == True,  # noqa: E712
            )
            .first()
        )

    def get_by_username(self, username: str) -> Optional[db_models.User]:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            User if found, None otherwise
        """
        return (
            self.db.query(db_models.User)
            .filter(db_models.User.username == username)
            .first()
        )

    def email_exists(self, email: str) -> bool:
        """
        Check if email already exists.

        Args:
            email: Email to check

        Returns:
            True if email exists, False otherwise
        """
        return (
            self.db.query(db_models.User).filter(db_models.User.email == email).first()
            is not None
        )

    def username_exists(self, username: str) -> bool:
        """
        Check if username already exists.

        Args:
            username: Username to check

        Returns:
            True if username exists, False otherwise
        """
        return (
            self.db.query(db_models.User)
            .filter(db_models.User.username == username)
            .first()
            is not None
        )

    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[db_models.User]:
        """
        Get all users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users
        """
        return self.db.query(db_models.User).offset(skip).limit(limit).all()

    def delete_user_and_related(self, user_id: int) -> bool:
        """
        Delete user and all related records.

        Args:
            user_id: User ID

        Returns:
            True if deleted, False if user not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return False

        # Delete related records (votes, comments, admin roles, ideas)
        self.db.query(db_models.Vote).filter(db_models.Vote.user_id == user_id).delete()
        self.db.query(db_models.Comment).filter(
            db_models.Comment.user_id == user_id
        ).delete()
        self.db.query(db_models.AdminRole).filter(
            db_models.AdminRole.user_id == user_id
        ).delete()
        self.db.query(db_models.Idea).filter(db_models.Idea.user_id == user_id).delete()

        # Delete user
        self.db.delete(user)
        self.db.commit()
        return True

    def get_admin_roles(self, user_id: int) -> List[db_models.AdminRole]:
        """
        Get admin roles for a user.

        Args:
            user_id: User ID

        Returns:
            List of admin roles
        """
        return (
            self.db.query(db_models.AdminRole)
            .filter(db_models.AdminRole.user_id == user_id)
            .all()
        )

    def has_admin_permission(
        self, user_id: int, category_id: Optional[int] = None
    ) -> bool:
        """
        Check if user has admin permission for a category.

        Args:
            user_id: User ID
            category_id: Category ID (None for global admin check)

        Returns:
            True if user has permission, False otherwise
        """
        user = self.get_by_id(user_id)
        if not user:
            return False

        # Check global admin
        if user.is_global_admin:
            return True

        # If no category specified, only global admin has permission
        if category_id is None:
            return False

        # Check category-specific admin role
        admin_role = (
            self.db.query(db_models.AdminRole)
            .filter(
                db_models.AdminRole.user_id == user_id,
                db_models.AdminRole.category_id == category_id,
            )
            .first()
        )

        return admin_role is not None

    def get_all_officials(self) -> List[db_models.User]:
        """
        Get all users with official status.

        Returns:
            List of official users ordered by verification date (newest first)
        """
        return (
            self.db.query(db_models.User)
            .filter(
                db_models.User.is_official == True,  # noqa: E712
                db_models.User.is_active == True,  # noqa: E712
            )
            .order_by(db_models.User.official_verified_at.desc())
            .all()
        )

    def get_pending_official_requests(self) -> List[db_models.User]:
        """
        Get all users who have requested official status.

        Returns:
            List of users with pending official requests
        """
        return (
            self.db.query(db_models.User)
            .filter(
                db_models.User.requests_official_status == True,  # noqa: E712
                db_models.User.is_official == False,  # noqa: E712
                db_models.User.is_active == True,  # noqa: E712
            )
            .order_by(db_models.User.official_request_at.asc())
            .all()
        )

    def get_all_users_filtered(
        self,
        include_inactive: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[db_models.User]:
        """
        Get all users with pagination and optional inactive filter.

        Args:
            include_inactive: Include inactive users
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users
        """
        query = self.db.query(db_models.User)

        if not include_inactive:
            query = query.filter(db_models.User.is_active == True)  # noqa: E712

        return query.offset(skip).limit(limit).all()

    def get_user_idea_stats(self, user_id: int) -> dict:
        """
        Get aggregated idea statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dict with total, approved, pending, rejected counts
        """
        from sqlalchemy import case, func

        result = (
            self.db.query(
                func.count(db_models.Idea.id).label("total"),
                func.sum(
                    case(
                        (db_models.Idea.status == db_models.IdeaStatus.APPROVED, 1),
                        else_=0,
                    )
                ).label("approved"),
                func.sum(
                    case(
                        (db_models.Idea.status == db_models.IdeaStatus.PENDING, 1),
                        else_=0,
                    )
                ).label("pending"),
                func.sum(
                    case(
                        (db_models.Idea.status == db_models.IdeaStatus.REJECTED, 1),
                        else_=0,
                    )
                ).label("rejected"),
            )
            .filter(db_models.Idea.user_id == user_id)
            .first()
        )

        return {
            "total": result.total or 0 if result else 0,
            "approved": result.approved or 0 if result else 0,
            "pending": result.pending or 0 if result else 0,
            "rejected": result.rejected or 0 if result else 0,
        }

    def get_user_votes_cast_stats(self, user_id: int) -> dict:
        """
        Get aggregated vote statistics for votes cast by a user.

        Args:
            user_id: User ID

        Returns:
            Dict with total, upvotes, downvotes counts
        """
        from sqlalchemy import case, func

        result = (
            self.db.query(
                func.count(db_models.Vote.id).label("total"),
                func.sum(
                    case(
                        (db_models.Vote.vote_type == db_models.VoteType.UPVOTE, 1),
                        else_=0,
                    )
                ).label("upvotes"),
                func.sum(
                    case(
                        (db_models.Vote.vote_type == db_models.VoteType.DOWNVOTE, 1),
                        else_=0,
                    )
                ).label("downvotes"),
            )
            .filter(db_models.Vote.user_id == user_id)
            .first()
        )

        return {
            "total": result.total or 0 if result else 0,
            "upvotes": result.upvotes or 0 if result else 0,
            "downvotes": result.downvotes or 0 if result else 0,
        }

    def count_user_comments(self, user_id: int) -> int:
        """
        Count comments made by a user.

        Args:
            user_id: User ID

        Returns:
            Number of comments
        """
        from sqlalchemy import func

        return (
            self.db.query(func.count(db_models.Comment.id))
            .filter(db_models.Comment.user_id == user_id)
            .scalar()
            or 0
        )

    def get_user_votes_received_stats(self, user_id: int) -> dict:
        """
        Get aggregated vote statistics for votes received on user's ideas.

        Args:
            user_id: User ID

        Returns:
            Dict with total, upvotes, downvotes counts
        """
        from sqlalchemy import case, func

        result = (
            self.db.query(
                func.count(db_models.Vote.id).label("total"),
                func.sum(
                    case(
                        (db_models.Vote.vote_type == db_models.VoteType.UPVOTE, 1),
                        else_=0,
                    )
                ).label("upvotes"),
                func.sum(
                    case(
                        (db_models.Vote.vote_type == db_models.VoteType.DOWNVOTE, 1),
                        else_=0,
                    )
                ).label("downvotes"),
            )
            .join(db_models.Idea, db_models.Vote.idea_id == db_models.Idea.id)
            .filter(db_models.Idea.user_id == user_id)
            .first()
        )

        return {
            "total": result.total or 0 if result else 0,
            "upvotes": result.upvotes or 0 if result else 0,
            "downvotes": result.downvotes or 0 if result else 0,
        }

    def count_user_idea_flags(self, user_id: int) -> int:
        """
        Count flags received on user's ideas.

        Args:
            user_id: User ID

        Returns:
            Number of flags
        """
        from sqlalchemy import func

        return (
            self.db.query(func.count(db_models.ContentFlag.id))
            .join(db_models.Idea, db_models.ContentFlag.content_id == db_models.Idea.id)
            .filter(
                db_models.ContentFlag.content_type == db_models.ContentType.IDEA,
                db_models.Idea.user_id == user_id,
            )
            .scalar()
            or 0
        )

    def count_user_comment_flags(self, user_id: int) -> int:
        """
        Count flags received on user's comments.

        Args:
            user_id: User ID

        Returns:
            Number of flags
        """
        from sqlalchemy import func

        return (
            self.db.query(func.count(db_models.ContentFlag.id))
            .join(
                db_models.Comment,
                db_models.ContentFlag.content_id == db_models.Comment.id,
            )
            .filter(
                db_models.ContentFlag.content_type == db_models.ContentType.COMMENT,
                db_models.Comment.user_id == user_id,
            )
            .scalar()
            or 0
        )

    def get_user_penalty_stats(self, user_id: int) -> dict:
        """
        Get penalty statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dict with total and active penalty counts
        """
        from sqlalchemy import case, func

        result = (
            self.db.query(
                func.count(db_models.UserPenalty.id).label("total"),
                func.sum(
                    case(
                        (
                            db_models.UserPenalty.status
                            == db_models.PenaltyStatus.ACTIVE,
                            1,
                        ),
                        else_=0,
                    )
                ).label("active"),
            )
            .filter(db_models.UserPenalty.user_id == user_id)
            .first()
        )

        return {
            "total": result.total or 0 if result else 0,
            "active": result.active or 0 if result else 0,
        }

    def count_user_votes(self, user_id: int) -> int:
        """
        Count votes cast by a user.

        Args:
            user_id: User ID

        Returns:
            Number of votes
        """
        from sqlalchemy import func

        return (
            self.db.query(func.count(db_models.Vote.id))
            .filter(db_models.Vote.user_id == user_id)
            .scalar()
            or 0
        )

    def get_recent_comments_with_author(self, user_id: int, limit: int = 5) -> list:
        """
        Get recent comments by a user with author info.

        Args:
            user_id: User ID
            limit: Maximum comments to return

        Returns:
            List of (Comment, username, display_name) tuples
        """
        return (
            self.db.query(
                db_models.Comment,
                db_models.User.username.label("author_username"),
                db_models.User.display_name.label("author_display_name"),
            )
            .join(db_models.User, db_models.Comment.user_id == db_models.User.id)
            .filter(db_models.Comment.user_id == user_id)
            .order_by(db_models.Comment.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_users_filtered_with_search(
        self,
        search: Optional[str] = None,
        include_inactive: bool = True,
        role: Optional[str] = None,
        is_official: Optional[bool] = None,
        is_banned: Optional[bool] = None,
        trust_score_min: Optional[int] = None,
        trust_score_max: Optional[int] = None,
        has_penalties: Optional[bool] = None,
        has_active_penalties: Optional[bool] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
    ) -> List[db_models.User]:
        """
        Get users with various filters for admin list.

        Args:
            search: Optional search term for name/email/username
            include_inactive: Include inactive users
            role: Filter by role (regular, category_admin, global_admin, official)
            is_official: Filter by official status
            is_banned: Filter by active ban status
            trust_score_min: Minimum trust score
            trust_score_max: Maximum trust score
            has_penalties: Filter users with any penalties
            has_active_penalties: Filter users with active penalties
            created_after: Registration date after
            created_before: Registration date before

        Returns:
            List of users matching filters
        """
        from sqlalchemy import exists, func, or_

        query = self.db.query(db_models.User)

        # Apply search filter
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(db_models.User.display_name).like(search_term),
                    func.lower(db_models.User.username).like(search_term),
                    func.lower(db_models.User.email).like(search_term),
                )
            )

        # Apply inactive filter
        if not include_inactive:
            query = query.filter(db_models.User.is_active)

        # Apply role filter
        if role:
            if role == "global_admin":
                query = query.filter(db_models.User.is_global_admin.is_(True))
            elif role == "official":
                query = query.filter(db_models.User.is_official.is_(True))
            elif role == "category_admin":
                query = query.filter(
                    exists().where(db_models.AdminRole.user_id == db_models.User.id)
                )
            elif role == "regular":
                query = query.filter(
                    db_models.User.is_global_admin.is_(False),
                    db_models.User.is_official.is_(False),
                    ~exists().where(db_models.AdminRole.user_id == db_models.User.id),
                )

        # Apply official filter
        if is_official is not None:
            query = query.filter(db_models.User.is_official.is_(is_official))

        # Apply trust score filters
        if trust_score_min is not None:
            query = query.filter(db_models.User.trust_score >= trust_score_min)
        if trust_score_max is not None:
            query = query.filter(db_models.User.trust_score <= trust_score_max)

        # Apply date filters
        if created_after is not None:
            query = query.filter(db_models.User.created_at >= created_after)
        if created_before is not None:
            query = query.filter(db_models.User.created_at <= created_before)

        # Apply ban status filter
        if is_banned is not None:
            ban_types = [
                db_models.PenaltyType.PERMANENT_BAN,
                db_models.PenaltyType.TEMP_BAN_24H,
                db_models.PenaltyType.TEMP_BAN_7D,
                db_models.PenaltyType.TEMP_BAN_30D,
            ]
            ban_subquery = exists().where(
                db_models.UserPenalty.user_id == db_models.User.id,
                db_models.UserPenalty.status == db_models.PenaltyStatus.ACTIVE,
                db_models.UserPenalty.penalty_type.in_(ban_types),
            )
            if is_banned:
                query = query.filter(ban_subquery)
            else:
                query = query.filter(~ban_subquery)

        # Apply penalties filter
        if has_penalties is not None:
            penalties_subquery = exists().where(
                db_models.UserPenalty.user_id == db_models.User.id
            )
            if has_penalties:
                query = query.filter(penalties_subquery)
            else:
                query = query.filter(~penalties_subquery)

        # Apply active penalties filter
        if has_active_penalties is not None:
            active_penalties_subquery = exists().where(
                db_models.UserPenalty.user_id == db_models.User.id,
                db_models.UserPenalty.status == db_models.PenaltyStatus.ACTIVE,
            )
            if has_active_penalties:
                query = query.filter(active_penalties_subquery)
            else:
                query = query.filter(~active_penalties_subquery)

        return query.all()

    def get_vote_scores_for_users(self, user_ids: List[int]) -> dict[int, int]:
        """
        Get vote scores (upvotes - downvotes) for multiple users' ideas.

        Args:
            user_ids: List of user IDs

        Returns:
            Dict mapping user_id to vote_score
        """
        if not user_ids:
            return {}

        from sqlalchemy import case, func

        result = (
            self.db.query(
                db_models.Idea.user_id.label("user_id"),
                func.sum(
                    case(
                        (db_models.Vote.vote_type == db_models.VoteType.UPVOTE, 1),
                        (db_models.Vote.vote_type == db_models.VoteType.DOWNVOTE, -1),
                        else_=0,
                    )
                ).label("vote_score"),
            )
            .join(db_models.Vote, db_models.Vote.idea_id == db_models.Idea.id)
            .filter(db_models.Idea.user_id.in_(user_ids))
            .group_by(db_models.Idea.user_id)
            .all()
        )

        return {row.user_id: row.vote_score or 0 for row in result}

    def get_category_admin_user_ids(self, user_ids: List[int]) -> set[int]:
        """
        Get user IDs that have category admin roles.

        Args:
            user_ids: List of user IDs to check

        Returns:
            Set of user IDs that are category admins
        """
        if not user_ids:
            return set()

        result = (
            self.db.query(db_models.AdminRole.user_id)
            .filter(db_models.AdminRole.user_id.in_(user_ids))
            .distinct()
            .all()
        )

        return {row.user_id for row in result}

    def get_penalty_counts_for_users(
        self, user_ids: List[int]
    ) -> dict[int, dict[str, int]]:
        """
        Get penalty counts (total and active) for multiple users.

        Args:
            user_ids: List of user IDs

        Returns:
            Dict mapping user_id to {"total": int, "active": int}
        """
        if not user_ids:
            return {}

        from sqlalchemy import case, func

        result = (
            self.db.query(
                db_models.UserPenalty.user_id.label("user_id"),
                func.count(db_models.UserPenalty.id).label("total"),
                func.sum(
                    case(
                        (
                            db_models.UserPenalty.status
                            == db_models.PenaltyStatus.ACTIVE,
                            1,
                        ),
                        else_=0,
                    )
                ).label("active"),
            )
            .filter(db_models.UserPenalty.user_id.in_(user_ids))
            .group_by(db_models.UserPenalty.user_id)
            .all()
        )

        return {
            row.user_id: {"total": row.total or 0, "active": row.active or 0}
            for row in result
        }

    def get_consent_logs(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[db_models.ConsentLog]:
        """
        Get consent logs for a user.

        Law 25 Compliance: Users have the right to access their consent history.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of consent logs ordered by most recent first
        """
        return (
            self.db.query(db_models.ConsentLog)
            .filter(db_models.ConsentLog.user_id == user_id)
            .order_by(db_models.ConsentLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
