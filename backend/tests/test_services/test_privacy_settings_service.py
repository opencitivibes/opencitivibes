"""Tests for PrivacySettingsService."""

import pytest
from sqlalchemy.orm import Session

from models import schemas
from models.exceptions import NotFoundException
from repositories.db_models import Comment, Idea, IdeaStatus, User
from services.privacy_settings_service import PrivacySettingsService


class TestGetPrivacySettings:
    """Tests for get_privacy_settings."""

    def test_returns_default_settings(self, db: Session, test_user: User) -> None:
        """Default settings should be public with all fields visible."""
        settings = PrivacySettingsService.get_privacy_settings(db, test_user.id)

        assert settings.profile_visibility == schemas.ProfileVisibility.PUBLIC
        assert settings.show_display_name is True
        assert settings.show_avatar is True
        assert settings.show_activity is True
        assert settings.show_join_date is True

    def test_raises_for_nonexistent_user(self, db: Session) -> None:
        """Should raise NotFoundException for nonexistent user."""
        with pytest.raises(NotFoundException):
            PrivacySettingsService.get_privacy_settings(db, 99999)


class TestUpdatePrivacySettings:
    """Tests for update_privacy_settings."""

    def test_updates_profile_visibility(self, db: Session, test_user: User) -> None:
        """Should update profile visibility."""
        update = schemas.PrivacySettingsUpdate(
            profile_visibility=schemas.ProfileVisibility.PRIVATE
        )

        result = PrivacySettingsService.update_privacy_settings(
            db, test_user.id, update
        )

        assert result.profile_visibility == schemas.ProfileVisibility.PRIVATE

    def test_updates_show_display_name(self, db: Session, test_user: User) -> None:
        """Should update show_display_name setting."""
        update = schemas.PrivacySettingsUpdate(show_display_name=False)

        result = PrivacySettingsService.update_privacy_settings(
            db, test_user.id, update
        )

        assert result.show_display_name is False

    def test_updates_multiple_settings(self, db: Session, test_user: User) -> None:
        """Should update multiple settings at once."""
        update = schemas.PrivacySettingsUpdate(
            profile_visibility=schemas.ProfileVisibility.REGISTERED,
            show_activity=False,
            show_join_date=False,
        )

        result = PrivacySettingsService.update_privacy_settings(
            db, test_user.id, update
        )

        assert result.profile_visibility == schemas.ProfileVisibility.REGISTERED
        assert result.show_activity is False
        assert result.show_join_date is False
        # Unchanged fields remain as they were
        assert result.show_display_name is True
        assert result.show_avatar is True

    def test_partial_update_preserves_other_fields(
        self, db: Session, test_user: User
    ) -> None:
        """Partial updates should not affect other fields."""
        # First update
        update1 = schemas.PrivacySettingsUpdate(show_avatar=False)
        PrivacySettingsService.update_privacy_settings(db, test_user.id, update1)

        # Second update
        update2 = schemas.PrivacySettingsUpdate(show_activity=False)
        result = PrivacySettingsService.update_privacy_settings(
            db, test_user.id, update2
        )

        assert result.show_avatar is False  # From first update
        assert result.show_activity is False  # From second update

    def test_raises_for_nonexistent_user(self, db: Session) -> None:
        """Should raise NotFoundException for nonexistent user."""
        update = schemas.PrivacySettingsUpdate(show_display_name=False)

        with pytest.raises(NotFoundException):
            PrivacySettingsService.update_privacy_settings(db, 99999, update)


class TestGetPublicProfile:
    """Tests for get_public_profile."""

    def test_public_profile_shows_all_fields(
        self, db: Session, test_user: User
    ) -> None:
        """Public profile should show all fields when visibility is public."""
        profile = PrivacySettingsService.get_public_profile(
            db, test_user.id, requesting_user=None
        )

        assert profile.id == test_user.id
        assert profile.username == test_user.username
        assert profile.display_name == test_user.display_name
        assert profile.profile_visibility == "public"

    def test_private_profile_hides_details_from_anonymous(
        self, db: Session, test_user: User
    ) -> None:
        """Private profile should hide details from anonymous users."""
        # Set profile to private
        test_user.profile_visibility = "private"
        db.commit()

        profile = PrivacySettingsService.get_public_profile(
            db, test_user.id, requesting_user=None
        )

        assert profile.id == test_user.id
        assert profile.username == test_user.username
        assert profile.display_name is None  # Hidden
        assert profile.avatar_url is None  # Hidden
        assert profile.created_at is None  # Hidden
        assert profile.profile_visibility == "private"

    def test_private_profile_visible_to_owner(
        self, db: Session, test_user: User
    ) -> None:
        """Owner should see their own private profile."""
        # Set profile to private
        test_user.profile_visibility = "private"
        db.commit()

        profile = PrivacySettingsService.get_public_profile(
            db, test_user.id, requesting_user=test_user
        )

        # Owner sees full profile
        assert profile.display_name == test_user.display_name

    def test_registered_only_hidden_from_anonymous(
        self, db: Session, test_user: User, other_user: User
    ) -> None:
        """Registered-only profile should be hidden from anonymous users."""
        # Set profile to registered-only
        test_user.profile_visibility = "registered"
        db.commit()

        # Anonymous user sees limited profile
        profile_anon = PrivacySettingsService.get_public_profile(
            db, test_user.id, requesting_user=None
        )
        assert profile_anon.display_name is None

        # Logged-in user sees full profile
        profile_logged = PrivacySettingsService.get_public_profile(
            db, test_user.id, requesting_user=other_user
        )
        assert profile_logged.display_name == test_user.display_name

    def test_individual_field_visibility(self, db: Session, test_user: User) -> None:
        """Individual field settings should be respected."""
        # Disable some fields
        test_user.show_display_name = False
        test_user.show_avatar = False
        test_user.show_activity = True
        test_user.show_join_date = True
        db.commit()

        profile = PrivacySettingsService.get_public_profile(
            db, test_user.id, requesting_user=None
        )

        assert profile.display_name is None  # Hidden
        assert profile.avatar_url is None  # Hidden
        assert profile.created_at is not None  # Visible

    def test_activity_counts_when_visible(
        self, db: Session, test_user: User, test_category
    ) -> None:
        """Activity counts should be shown when show_activity is True."""
        # Create some content
        idea = Idea(
            title="Test Idea",
            description="Test",
            user_id=test_user.id,
            category_id=test_category.id,
            status=IdeaStatus.APPROVED,
        )
        db.add(idea)

        comment = Comment(
            content="Test comment",
            user_id=test_user.id,
            idea_id=1,  # Will be set after idea is committed
        )

        db.commit()
        comment.idea_id = idea.id
        db.add(comment)
        db.commit()

        test_user.show_activity = True
        db.commit()

        profile = PrivacySettingsService.get_public_profile(
            db, test_user.id, requesting_user=None
        )

        assert profile.idea_count is not None
        assert profile.comment_count is not None

    def test_activity_counts_hidden_when_disabled(
        self, db: Session, test_user: User
    ) -> None:
        """Activity counts should be None when show_activity is False."""
        test_user.show_activity = False
        db.commit()

        profile = PrivacySettingsService.get_public_profile(
            db, test_user.id, requesting_user=None
        )

        assert profile.idea_count is None
        assert profile.comment_count is None

    def test_raises_for_nonexistent_user(self, db: Session) -> None:
        """Should raise NotFoundException for nonexistent user."""
        with pytest.raises(NotFoundException):
            PrivacySettingsService.get_public_profile(db, 99999, requesting_user=None)
