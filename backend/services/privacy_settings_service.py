"""
Privacy Settings Service for Law 25 Compliance.

Manages user privacy preferences and applies them to profile visibility.

Law 25 Articles:
- Article 9.1: Privacy-protective settings must be the default
- Article 10: Users must be able to control their personal information
"""

from typing import Optional

from sqlalchemy.orm import Session

from models import schemas
from models.exceptions import NotFoundException
from repositories import db_models
from repositories.privacy_repository import PrivacyRepository
from repositories.user_repository import UserRepository


class PrivacySettingsService:
    """Service for managing user privacy settings."""

    @staticmethod
    def get_privacy_settings(db: Session, user_id: int) -> schemas.PrivacySettings:
        """
        Get user's current privacy settings.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Current privacy settings

        Raises:
            NotFoundException: If user not found
        """
        user = UserRepository(db).get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        return schemas.PrivacySettings(
            profile_visibility=schemas.ProfileVisibility(user.profile_visibility),
            show_display_name=user.show_display_name,
            show_avatar=user.show_avatar,
            show_activity=user.show_activity,
            show_join_date=user.show_join_date,
        )

    @staticmethod
    def update_privacy_settings(
        db: Session,
        user_id: int,
        settings_update: schemas.PrivacySettingsUpdate,
    ) -> schemas.PrivacySettings:
        """
        Update user's privacy settings.

        Args:
            db: Database session
            user_id: User ID
            settings_update: New settings values

        Returns:
            Updated privacy settings

        Raises:
            NotFoundException: If user not found
        """
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        # Update only provided fields
        if settings_update.profile_visibility is not None:
            user.profile_visibility = settings_update.profile_visibility.value

        if settings_update.show_display_name is not None:
            user.show_display_name = settings_update.show_display_name

        if settings_update.show_avatar is not None:
            user.show_avatar = settings_update.show_avatar

        if settings_update.show_activity is not None:
            user.show_activity = settings_update.show_activity

        if settings_update.show_join_date is not None:
            user.show_join_date = settings_update.show_join_date

        # Use repository's update method for commit
        user_repo.update(user)

        return schemas.PrivacySettings(
            profile_visibility=schemas.ProfileVisibility(user.profile_visibility),
            show_display_name=user.show_display_name,
            show_avatar=user.show_avatar,
            show_activity=user.show_activity,
            show_join_date=user.show_join_date,
        )

    @staticmethod
    def _build_minimal_profile(
        target_user: db_models.User,
        visibility: str,
    ) -> schemas.UserPublicFiltered:
        """
        Build minimal profile for restricted visibility.

        Returns only username and official status, hiding all other details.

        Args:
            target_user: User whose profile to build
            visibility: Current visibility setting

        Returns:
            Minimal public profile
        """
        return schemas.UserPublicFiltered(
            id=target_user.id,
            username=target_user.username,
            is_official=target_user.is_official,
            official_title=target_user.official_title
            if target_user.is_official
            else None,
            profile_visibility=visibility,
        )

    @staticmethod
    def _build_full_profile(
        db: Session,
        target_user: db_models.User,
        target_user_id: int,
    ) -> schemas.UserPublicFiltered:
        """
        Build full profile with privacy settings applied.

        Respects individual field visibility settings (show_display_name, etc.).

        Args:
            db: Database session
            target_user: User whose profile to build
            target_user_id: User ID

        Returns:
            Full public profile with privacy settings applied
        """
        profile = schemas.UserPublicFiltered(
            id=target_user.id,
            username=target_user.username,
            is_official=target_user.is_official,
            official_title=target_user.official_title
            if target_user.is_official
            else None,
            profile_visibility=target_user.profile_visibility,
        )

        # Apply individual field settings
        if target_user.show_display_name:
            profile.display_name = target_user.display_name

        if target_user.show_avatar:
            profile.avatar_url = target_user.avatar_url

        if target_user.show_join_date:
            profile.created_at = target_user.created_at

        if target_user.show_activity:
            privacy_repo = PrivacyRepository(db)
            profile.idea_count = privacy_repo.get_user_approved_idea_count(
                target_user_id
            )
            profile.comment_count = privacy_repo.get_user_comment_count(target_user_id)

        return profile

    @staticmethod
    def get_public_profile(
        db: Session,
        target_user_id: int,
        requesting_user: Optional[db_models.User] = None,
    ) -> schemas.UserPublicFiltered:
        """
        Get public profile with privacy settings applied.

        Visibility levels:
        - public: Anyone can see full profile
        - registered: Only logged-in users see full profile
        - private: Only the owner sees full profile

        Individual fields can also be hidden via show_* settings.

        Args:
            db: Database session
            target_user_id: User ID to view
            requesting_user: Currently logged-in user (or None for anonymous)

        Returns:
            Public profile with appropriate fields visible

        Raises:
            NotFoundException: If user not found
        """
        target_user = UserRepository(db).get_by_id(target_user_id)
        if not target_user:
            raise NotFoundException("User not found")

        visibility = target_user.profile_visibility
        is_owner = requesting_user and requesting_user.id == target_user_id
        is_logged_in = requesting_user is not None

        # Private: only owner sees full profile
        if visibility == "private" and not is_owner:
            return PrivacySettingsService._build_minimal_profile(
                target_user, visibility
            )

        # Registered: only logged-in users see full profile
        if visibility == "registered" and not is_logged_in:
            return PrivacySettingsService._build_minimal_profile(
                target_user, visibility
            )

        # Build full profile with individual field settings applied
        return PrivacySettingsService._build_full_profile(
            db, target_user, target_user_id
        )
