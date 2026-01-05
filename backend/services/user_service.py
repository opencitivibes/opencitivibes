"""
User Service

Handles user management operations including admin role assignment.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from models.exceptions import (
    NotFoundException,
    ValidationException,
)
from repositories.user_repository import UserRepository

# Avatar upload configuration
ALLOWED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB


class UserService:
    """Service for managing users and admin roles."""

    @staticmethod
    def get_all_users(
        db: Session, skip: int = 0, limit: int = 100, include_inactive: bool = True
    ) -> List[db_models.User]:
        """
        Get all users with pagination.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_inactive: Include inactive users

        Returns:
            List of users
        """
        user_repo = UserRepository(db)
        return user_repo.get_all_users_filtered(
            include_inactive=include_inactive,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_users_with_reputation(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        include_inactive: bool = True,
        role: Optional[str] = None,
        is_official: Optional[bool] = None,
        is_banned: Optional[bool] = None,
        trust_score_min: Optional[int] = None,
        trust_score_max: Optional[int] = None,
        vote_score_min: Optional[int] = None,
        vote_score_max: Optional[int] = None,
        has_penalties: Optional[bool] = None,
        has_active_penalties: Optional[bool] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
    ) -> tuple[List[dict], int]:
        """
        Get users with reputation data for admin list.

        Uses optimized queries to compute vote_score and penalty counts
        in a single query using subqueries.

        Args:
            db: Database session
            page: Page number (1-indexed)
            page_size: Number of users per page
            search: Optional search term for name/email/username
            include_inactive: Include inactive users
            role: Filter by role (regular, category_admin, global_admin, official)
            is_official: Filter by official status
            is_banned: Filter by active ban status
            trust_score_min: Minimum trust score (0-100)
            trust_score_max: Maximum trust score (0-100)
            vote_score_min: Minimum vote score
            vote_score_max: Maximum vote score
            has_penalties: Filter users with any penalties
            has_active_penalties: Filter users with active penalties
            created_after: Registration date after
            created_before: Registration date before

        Returns:
            Tuple of (list of user dicts with reputation, total count)
        """
        user_repo = UserRepository(db)

        # Get all matching users using repository
        all_matching_users = user_repo.get_users_filtered_with_search(
            search=search,
            include_inactive=include_inactive,
            role=role,
            is_official=is_official,
            is_banned=is_banned,
            trust_score_min=trust_score_min,
            trust_score_max=trust_score_max,
            has_penalties=has_penalties,
            has_active_penalties=has_active_penalties,
            created_after=created_after,
            created_before=created_before,
        )
        all_user_ids = [u.id for u in all_matching_users]

        # Get vote scores for all matching users
        vote_scores = user_repo.get_vote_scores_for_users(all_user_ids)

        # Filter by vote score if specified
        if vote_score_min is not None or vote_score_max is not None:
            filtered_user_ids = []
            for user_id in all_user_ids:
                score = vote_scores.get(user_id, 0)
                if vote_score_min is not None and score < vote_score_min:
                    continue
                if vote_score_max is not None and score > vote_score_max:
                    continue
                filtered_user_ids.append(user_id)
            all_user_ids = filtered_user_ids
            # Reapply filter
            all_matching_users = [u for u in all_matching_users if u.id in all_user_ids]

        # Get total count (after all filters)
        total = len(all_matching_users)

        # Get paginated users
        skip = (page - 1) * page_size
        users = all_matching_users[skip : skip + page_size]

        if not users:
            return [], total

        user_ids = [u.id for u in users]

        # Get category admin info for these users
        category_admin_ids = user_repo.get_category_admin_user_ids(user_ids)

        # Compute penalty counts for each user
        penalty_counts = user_repo.get_penalty_counts_for_users(user_ids)

        # Build result list
        result = []
        for user in users:
            user_id = user.id
            penalties = penalty_counts.get(user_id, {"total": 0, "active": 0})
            result.append(
                {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "display_name": user.display_name,
                    "is_active": user.is_active,
                    "is_global_admin": user.is_global_admin,
                    "is_official": user.is_official,
                    "official_title": user.official_title,
                    "has_category_admin_role": user_id in category_admin_ids,
                    "created_at": user.created_at,
                    "trust_score": user.trust_score,
                    "vote_score": vote_scores.get(user_id, 0),
                    "penalty_count": penalties["total"],
                    "active_penalty_count": penalties["active"],
                }
            )

        return result, total

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[db_models.User]:
        """
        Get user by ID.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            User object or None
        """
        user_repo = UserRepository(db)
        return user_repo.get_by_id(user_id)

    @staticmethod
    def get_user_by_id_or_raise(db: Session, user_id: int) -> db_models.User:
        """
        Get user by ID or raise NotFoundException.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            User object

        Raises:
            NotFoundException: If user not found
        """
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        return user

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[db_models.User]:
        """
        Get user by email.

        Args:
            db: Database session
            email: User email

        Returns:
            User object or None
        """
        user_repo = UserRepository(db)
        return user_repo.get_by_email(email)

    @staticmethod
    def update_user(
        db: Session, user_id: int, user_update: schemas.UserUpdate
    ) -> db_models.User:
        """
        Update user properties (admin only).

        Args:
            db: Database session
            user_id: User ID
            user_update: Updated user data

        Returns:
            Updated user

        Raises:
            NotFoundException: If user not found
        """
        db_user = UserService.get_user_by_id(db, user_id)
        if not db_user:
            raise NotFoundException("User not found")

        # Update only provided fields
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)

        user_repo = UserRepository(db)
        user_repo.commit()
        user_repo.refresh(db_user)
        return db_user

    @staticmethod
    def delete_user(
        db: Session, user_id: int, requesting_user_id: Optional[int] = None
    ) -> bool:
        """
        Delete a user and all associated data.

        Args:
            db: Database session
            user_id: User ID
            requesting_user_id: ID of the user making the request (for self-deletion check)

        Returns:
            True if deleted successfully

        Raises:
            NotFoundException: If user not found
            ValidationException: If trying to delete own account
        """
        from repositories.admin_role_repository import AdminRoleRepository
        from repositories.comment_repository import CommentRepository
        from repositories.idea_repository import IdeaRepository
        from repositories.vote_repository import VoteRepository

        # Prevent self-deletion
        if requesting_user_id is not None and user_id == requesting_user_id:
            raise ValidationException("Cannot delete your own account")

        user_repo = UserRepository(db)
        db_user = user_repo.get_by_id(user_id)
        if not db_user:
            raise NotFoundException("User not found")

        # Delete associated data using repositories
        vote_repo = VoteRepository(db)
        vote_repo.delete_by_user_id(user_id)

        comment_repo = CommentRepository(db)
        comment_repo.delete_by_user_id(user_id)

        admin_role_repo = AdminRoleRepository(db)
        admin_role_repo.delete_by_user_id(user_id)

        idea_repo = IdeaRepository(db)
        idea_repo.delete_by_user_id(user_id)

        # Finally delete the user
        user_repo.delete(db_user)
        return True

    @staticmethod
    def assign_admin_role(
        db: Session, user_id: int, category_id: Optional[int] = None
    ) -> db_models.AdminRole:
        """
        Assign admin role to a user.

        Args:
            db: Database session
            user_id: User ID
            category_id: Category ID (None for global admin)

        Returns:
            Created admin role

        Raises:
            NotFoundException: If user not found or category not found
            ValidationException: If role already exists
        """
        from repositories.admin_role_repository import AdminRoleRepository
        from repositories.category_repository import CategoryRepository

        # Check if user exists
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        # Check if category exists (if specified)
        if category_id:
            category_repo = CategoryRepository(db)
            category = category_repo.get_by_id(category_id)
            if not category:
                raise NotFoundException("Category not found")

        # Check if role already exists
        admin_role_repo = AdminRoleRepository(db)
        existing_role = admin_role_repo.get_by_user_and_category(user_id, category_id)

        if existing_role:
            raise ValidationException(
                "Admin role already exists for this user and category"
            )

        # Create new admin role
        admin_role = db_models.AdminRole(user_id=user_id, category_id=category_id)
        return admin_role_repo.create(admin_role)

    @staticmethod
    def remove_admin_role(
        db: Session, user_id: int, category_id: Optional[int] = None
    ) -> bool:
        """
        Remove admin role from a user.

        Args:
            db: Database session
            user_id: User ID
            category_id: Category ID (None for global admin)

        Returns:
            True if removed successfully

        Raises:
            NotFoundException: If role not found
        """
        from repositories.admin_role_repository import AdminRoleRepository

        admin_role_repo = AdminRoleRepository(db)
        admin_role = admin_role_repo.get_by_user_and_category(user_id, category_id)

        if not admin_role:
            raise NotFoundException("Admin role not found")

        admin_role_repo.delete(admin_role)
        return True

    @staticmethod
    def get_user_admin_roles(db: Session, user_id: int) -> List[db_models.AdminRole]:
        """
        Get all admin roles for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of admin roles
        """
        from repositories.admin_role_repository import AdminRoleRepository

        admin_role_repo = AdminRoleRepository(db)
        return admin_role_repo.get_by_user_id(user_id)

    @staticmethod
    def is_global_admin(db: Session, user_id: int) -> bool:
        """
        Check if user is a global admin.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            True if user is global admin
        """
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            return False

        return bool(user.is_global_admin)

    @staticmethod
    def is_category_admin(db: Session, user_id: int, category_id: int) -> bool:
        """
        Check if user is admin for a specific category.

        Args:
            db: Database session
            user_id: User ID
            category_id: Category ID

        Returns:
            True if user is admin for the category
        """
        from repositories.admin_role_repository import AdminRoleRepository

        # Global admins have access to all categories
        if UserService.is_global_admin(db, user_id):
            return True

        # Check for specific category admin role
        admin_role_repo = AdminRoleRepository(db)
        return admin_role_repo.is_category_admin(user_id, category_id)

    @staticmethod
    def get_user_statistics(db: Session, user_id: int) -> schemas.UserStatistics:
        """
        Get statistics for a user.

        Uses optimized queries with conditional counting to minimize database
        round trips (was 11 queries, now 4 queries).

        Args:
            db: Database session
            user_id: User ID

        Returns:
            UserStatistics schema with comprehensive user statistics

        Raises:
            NotFoundException: If user not found
        """
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise NotFoundException("User not found")

        user_repo = UserRepository(db)

        # Optimized: Single query for all idea counts by status
        idea_stats = user_repo.get_user_idea_stats(user_id)
        total_ideas = idea_stats["total"]
        approved_ideas = idea_stats["approved"]
        pending_ideas = idea_stats["pending"]
        rejected_ideas = idea_stats["rejected"]

        # Optimized: Single query for votes cast by user
        votes_cast_stats = user_repo.get_user_votes_cast_stats(user_id)
        votes_cast = votes_cast_stats["total"]
        upvotes_cast = votes_cast_stats["upvotes"]
        downvotes_cast = votes_cast_stats["downvotes"]

        # Count comments made by user
        comments_made = user_repo.count_user_comments(user_id)

        # Optimized: Single query for votes received on user's ideas
        votes_received_stats = user_repo.get_user_votes_received_stats(user_id)
        votes_received = votes_received_stats["total"]
        upvotes_received = votes_received_stats["upvotes"]
        downvotes_received = votes_received_stats["downvotes"]

        # Moderation stats: Flags received on user's content (ideas + comments)
        idea_flags = user_repo.count_user_idea_flags(user_id)
        comment_flags = user_repo.count_user_comment_flags(user_id)

        # Penalty stats: count by status
        penalty_stats = user_repo.get_user_penalty_stats(user_id)
        total_penalties = penalty_stats["total"]
        active_penalties = penalty_stats["active"]

        return schemas.UserStatistics(
            user_id=user_id,
            username=str(user.username),
            display_name=str(user.display_name),
            email=str(user.email),
            is_active=bool(user.is_active),
            is_global_admin=bool(user.is_global_admin),
            created_at=user.created_at,  # type: ignore[arg-type]
            ideas=schemas.UserIdeaStats(
                total=total_ideas,
                approved=approved_ideas,
                pending=pending_ideas,
                rejected=rejected_ideas,
            ),
            votes_cast=schemas.UserVotesCast(
                total=votes_cast,
                upvotes=upvotes_cast,
                downvotes=downvotes_cast,
            ),
            votes_received=schemas.UserVotesReceived(
                total=votes_received,
                upvotes=upvotes_received,
                downvotes=downvotes_received,
                score=upvotes_received - downvotes_received,
            ),
            comments_made=comments_made,
            moderation=schemas.UserModerationStats(
                trust_score=int(user.trust_score),  # type: ignore[arg-type]
                flags_received=schemas.UserFlagsReceived(
                    total=idea_flags + comment_flags,
                    on_ideas=idea_flags,
                    on_comments=comment_flags,
                ),
                penalties=schemas.UserPenaltyStats(
                    total=total_penalties,
                    active=active_penalties,
                ),
            ),
        )

    @staticmethod
    def register_user(
        db: Session,
        user_data: schemas.UserCreate,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> db_models.User:
        """
        Register a new user with consent tracking.

        Args:
            db: Database session
            user_data: User registration data including consent fields
            ip_address: Client IP for consent audit log
            user_agent: Client user agent for consent audit log

        Returns:
            Created user

        Raises:
            ValidationException: If email/username exists, password invalid,
                                 or required consents not provided
        """
        from helpers.password_validation import validate_password_complexity

        from models.config import settings

        user_repo = UserRepository(db)

        # Validate consent (Law 25 compliance)
        if not user_data.accepts_terms:
            raise ValidationException(
                "You must accept the Terms of Service to register"
            )
        if not user_data.accepts_privacy_policy:
            raise ValidationException("You must accept the Privacy Policy to register")

        # Validate password complexity
        is_valid, errors = validate_password_complexity(user_data.password)
        if not is_valid:
            raise ValidationException("; ".join(errors))

        # Check if email already exists
        if user_repo.get_by_email(user_data.email):
            raise ValidationException("Email already registered")

        # Check if username already exists
        if user_repo.get_by_username(user_data.username):
            raise ValidationException("Username already taken")

        # Get current policy versions
        current_terms_version = settings.TERMS_VERSION
        current_privacy_version = settings.PRIVACY_POLICY_VERSION

        # Hash password and create user with consent fields
        now = datetime.now(timezone.utc)
        hashed_password = auth.get_password_hash(user_data.password)
        new_user = db_models.User(
            email=user_data.email,
            username=user_data.username,
            display_name=user_data.display_name,
            hashed_password=hashed_password,
            requests_official_status=user_data.requests_official_status or False,
            official_title_request=user_data.official_title_request
            if user_data.requests_official_status
            else None,
            official_request_at=now if user_data.requests_official_status else None,
            # Consent fields (Law 25)
            consent_terms_accepted=True,
            consent_privacy_accepted=True,
            consent_terms_version=current_terms_version,
            consent_privacy_version=current_privacy_version,
            consent_timestamp=now,
            marketing_consent=user_data.marketing_consent,
            marketing_consent_timestamp=now if user_data.marketing_consent else None,
        )

        user_repo.add(new_user)
        user_repo.flush()  # Get user ID before creating consent logs

        # Create consent audit log entries
        consent_logs = [
            db_models.ConsentLog(
                user_id=new_user.id,
                consent_type="terms",
                action="granted",
                policy_version=current_terms_version,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None,
            ),
            db_models.ConsentLog(
                user_id=new_user.id,
                consent_type="privacy",
                action="granted",
                policy_version=current_privacy_version,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None,
            ),
        ]

        if user_data.marketing_consent:
            consent_logs.append(
                db_models.ConsentLog(
                    user_id=new_user.id,
                    consent_type="marketing",
                    action="granted",
                    policy_version=None,
                    ip_address=ip_address,
                    user_agent=user_agent[:500] if user_agent else None,
                )
            )

        user_repo.add_all(consent_logs)  # type: ignore[arg-type]
        user_repo.commit()
        user_repo.refresh(new_user)

        return new_user

    @staticmethod
    def update_profile(
        db: Session, user_id: int, profile_update: schemas.UserProfileUpdate
    ) -> db_models.User:
        """
        Update user profile (display_name, email).

        Args:
            db: Database session
            user_id: User ID
            profile_update: Profile update data

        Returns:
            Updated user

        Raises:
            NotFoundException: If user not found
            ValidationException: If email already in use
        """
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        # Check if email is being changed and if it's already taken
        if profile_update.email and profile_update.email != str(user.email):
            existing_user = user_repo.get_by_email(profile_update.email)
            if existing_user and int(existing_user.id) != user_id:  # type: ignore[arg-type]
                raise ValidationException("Email already in use")
            user.email = profile_update.email  # type: ignore[assignment]

        # Update display_name if provided
        if profile_update.display_name:
            user.display_name = profile_update.display_name  # type: ignore[assignment]

        return user_repo.update(user)

    @staticmethod
    def change_password(
        db: Session, user_id: int, current_password: str, new_password: str
    ) -> bool:
        """
        Change user password.

        Args:
            db: Database session
            user_id: User ID
            current_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully

        Raises:
            NotFoundException: If user not found
            ValidationException: If current password incorrect or new password invalid
        """
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        # Verify current password
        if not auth.verify_password(current_password, str(user.hashed_password)):
            raise ValidationException("Current password is incorrect")

        # Validate new password complexity
        from helpers.password_validation import validate_password_complexity

        is_valid, errors = validate_password_complexity(new_password)
        if not is_valid:
            raise ValidationException("; ".join(errors))

        # Hash and update password
        user.hashed_password = auth.get_password_hash(new_password)  # type: ignore[assignment]
        user_repo.update(user)
        return True

    @staticmethod
    def get_activity_history(db: Session, user_id: int) -> schemas.UserActivityHistory:
        """
        Get user activity history with statistics and recent items.

        Uses optimized queries with conditional counting to minimize database
        round trips (was 6 queries for counts, now 3 queries).

        Args:
            db: Database session
            user_id: User ID

        Returns:
            User activity history

        Raises:
            NotFoundException: If user not found
        """
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        # Optimized: Single query for all idea counts by status
        idea_stats = user_repo.get_user_idea_stats(user_id)
        ideas_count = idea_stats["total"]
        approved_ideas_count = idea_stats["approved"]
        pending_ideas_count = idea_stats["pending"]
        rejected_ideas_count = idea_stats["rejected"]

        # Count votes
        votes_count = user_repo.count_user_votes(user_id)

        # Count comments
        comments_count = user_repo.count_user_comments(user_id)

        # Get recent ideas
        from services.idea_service import IdeaService

        recent_ideas = IdeaService.get_my_ideas(db, user_id=user_id, skip=0, limit=5)

        # Get recent comments
        recent_comments_query = user_repo.get_recent_comments_with_author(user_id, 5)

        recent_comments = []
        for comment, username, display_name in recent_comments_query:
            comment_dict = {
                "id": comment.id,
                "idea_id": comment.idea_id,
                "user_id": comment.user_id,
                "content": comment.content,
                "is_moderated": comment.is_moderated,
                "created_at": comment.created_at,
                "author_username": username,
                "author_display_name": display_name or username,
                # Moderation status for user's own view
                "is_deleted": comment.deleted_at is not None,
                "deletion_reason": comment.deletion_reason,
                "is_hidden": comment.is_hidden,
            }
            recent_comments.append(schemas.Comment(**comment_dict))

        return schemas.UserActivityHistory(
            ideas_count=ideas_count,
            approved_ideas_count=approved_ideas_count,
            pending_ideas_count=pending_ideas_count,
            rejected_ideas_count=rejected_ideas_count,
            votes_count=votes_count,
            comments_count=comments_count,
            recent_ideas=recent_ideas,
            recent_comments=recent_comments,
        )

    @staticmethod
    def upload_avatar(
        db: Session, user_id: int, file: UploadFile
    ) -> schemas.AvatarUploadResponse:
        """
        Upload user avatar with security validation.

        Args:
            db: Database session
            user_id: User ID
            file: Avatar image file

        Returns:
            AvatarUploadResponse with message and avatar_url

        Raises:
            NotFoundException: If user not found
            ValidationException: If file invalid (type, size, or content)
        """
        import uuid

        import magic

        # Allowed MIME types and their extensions
        allowed_mime_types = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }
        max_avatar_size = 5 * 1024 * 1024  # 5MB

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        # Read file content for validation
        content = file.file.read()
        file.file.seek(0)  # Reset for potential re-read

        # Validate file size
        if len(content) > max_avatar_size:
            raise ValidationException("File size exceeds 5MB limit")

        # Validate actual file content using python-magic (not just headers)
        detected_type = magic.from_buffer(content, mime=True)
        if detected_type not in allowed_mime_types:
            raise ValidationException(
                f"Invalid file type '{detected_type}'. "
                f"Allowed: {', '.join(allowed_mime_types.keys())}"
            )

        # Generate unpredictable filename using UUID
        extension = allowed_mime_types[detected_type]
        filename = f"{uuid.uuid4()}{extension}"

        # Create uploads directory if it doesn't exist
        upload_dir = Path("data/uploads/avatars")
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / filename

        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # Delete old avatar if exists
        avatar_url_str = str(user.avatar_url) if user.avatar_url is not None else ""  # type: ignore[truthy-bool]
        if avatar_url_str:
            # Convert forward slashes to system path separators
            old_file_path = Path(avatar_url_str.replace("/", os.sep))
            if old_file_path.exists():
                old_file_path.unlink()

        # Update user avatar_url (use forward slashes for URL compatibility)
        avatar_url = str(file_path).replace("\\", "/")
        user.avatar_url = avatar_url  # type: ignore[assignment]
        user_repo.update(user)

        return schemas.AvatarUploadResponse(
            message="Avatar uploaded successfully", avatar_url=avatar_url
        )

    @staticmethod
    def get_consent_status(db: Session, user_id: int) -> schemas.ConsentStatus:
        """
        Get current consent status for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            ConsentStatus schema

        Raises:
            NotFoundException: If user not found
        """
        from models.config import settings

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        requires_reconsent = (
            user.consent_terms_version != settings.TERMS_VERSION
            or user.consent_privacy_version != settings.PRIVACY_POLICY_VERSION
        )

        return schemas.ConsentStatus(
            terms_accepted=bool(user.consent_terms_accepted),
            terms_version=user.consent_terms_version,
            privacy_accepted=bool(user.consent_privacy_accepted),
            privacy_version=user.consent_privacy_version,
            marketing_consent=bool(user.marketing_consent),
            consent_timestamp=user.consent_timestamp,
            requires_reconsent=requires_reconsent,
        )

    @staticmethod
    def get_consent_history(
        db: Session, user_id: int
    ) -> list[schemas.ConsentLogExport]:
        """
        Get consent history for a user.

        Law 25 Compliance: Users have the right to access all their personal data,
        including the history of consent changes.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of consent log entries ordered by most recent first
        """
        from repositories.user_repository import UserRepository

        user_repo = UserRepository(db)

        # Get all consent logs for this user
        logs = user_repo.get_consent_logs(user_id)

        return [
            schemas.ConsentLogExport(
                consent_type=log.consent_type,
                action=log.action,
                policy_version=log.policy_version,
                created_at=log.created_at,
            )
            for log in logs
        ]

    @staticmethod
    def update_consent(
        db: Session,
        user_id: int,
        consent_update: schemas.ConsentUpdate,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> schemas.ConsentStatus:
        """
        Update user consent preferences with audit logging.

        Args:
            db: Database session
            user_id: User ID
            consent_update: New consent preferences
            ip_address: Client IP for audit log
            user_agent: Client user agent for audit log

        Returns:
            Updated ConsentStatus

        Raises:
            NotFoundException: If user not found
        """
        from models.config import settings

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        now = datetime.now(timezone.utc)
        consent_logs: list[db_models.ConsentLog] = []

        # Handle marketing consent change
        if consent_update.marketing_consent is not None:
            old_value = user.marketing_consent
            new_value = consent_update.marketing_consent

            if old_value != new_value:
                user.marketing_consent = new_value  # type: ignore[assignment]
                user.marketing_consent_timestamp = now  # type: ignore[assignment]

                consent_logs.append(
                    db_models.ConsentLog(
                        user_id=user_id,
                        consent_type="marketing",
                        action="granted" if new_value else "withdrawn",
                        policy_version=None,
                        ip_address=ip_address,
                        user_agent=user_agent[:500] if user_agent else None,
                    )
                )

        # Handle terms re-consent
        if consent_update.accepts_terms is True:
            user.consent_terms_accepted = True  # type: ignore[assignment]
            user.consent_terms_version = settings.TERMS_VERSION  # type: ignore[assignment]
            user.consent_timestamp = now  # type: ignore[assignment]

            consent_logs.append(
                db_models.ConsentLog(
                    user_id=user_id,
                    consent_type="terms",
                    action="updated",
                    policy_version=settings.TERMS_VERSION,
                    ip_address=ip_address,
                    user_agent=user_agent[:500] if user_agent else None,
                )
            )

        # Handle privacy re-consent
        if consent_update.accepts_privacy_policy is True:
            user.consent_privacy_accepted = True  # type: ignore[assignment]
            user.consent_privacy_version = settings.PRIVACY_POLICY_VERSION  # type: ignore[assignment]
            user.consent_timestamp = now  # type: ignore[assignment]

            consent_logs.append(
                db_models.ConsentLog(
                    user_id=user_id,
                    consent_type="privacy",
                    action="updated",
                    policy_version=settings.PRIVACY_POLICY_VERSION,
                    ip_address=ip_address,
                    user_agent=user_agent[:500] if user_agent else None,
                )
            )

        # Save changes
        if consent_logs:
            user_repo.add_all(consent_logs)  # type: ignore[arg-type]
        user_repo.commit()
        user_repo.refresh(user)

        # Return updated status
        requires_reconsent = (
            user.consent_terms_version != settings.TERMS_VERSION
            or user.consent_privacy_version != settings.PRIVACY_POLICY_VERSION
        )

        return schemas.ConsentStatus(
            terms_accepted=bool(user.consent_terms_accepted),
            terms_version=user.consent_terms_version,
            privacy_accepted=bool(user.consent_privacy_accepted),
            privacy_version=user.consent_privacy_version,
            marketing_consent=bool(user.marketing_consent),
            consent_timestamp=user.consent_timestamp,
            requires_reconsent=requires_reconsent,
        )
