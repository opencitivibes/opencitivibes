"""
Unit tests for UserService.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

import models.schemas as schemas
import repositories.db_models as db_models
from models.exceptions import NotFoundException, ValidationException
from services.user_service import UserService


class TestGetAllUsers:
    """Tests for UserService.get_all_users."""

    def test_get_all_users_empty(self, db_session: Session):
        """Should return empty list when no users exist."""
        # Clear any existing users
        db_session.query(db_models.User).delete()
        db_session.commit()

        result = UserService.get_all_users(db_session)
        assert result == []

    def test_get_all_users(self, db_session: Session, test_user: db_models.User):
        """Should return all users."""
        result = UserService.get_all_users(db_session)
        assert len(result) >= 1

    def test_get_all_users_exclude_inactive(self, db_session: Session):
        """Should exclude inactive users when include_inactive=False."""
        # Create inactive user
        inactive_user = db_models.User(
            email="inactive@test.com",
            username="inactive",
            display_name="Inactive",
            hashed_password="hash",
            is_active=False,
        )
        db_session.add(inactive_user)
        db_session.commit()

        result = UserService.get_all_users(db_session, include_inactive=False)
        assert all(u.is_active for u in result)

    def test_get_all_users_pagination(self, db_session: Session):
        """Should support pagination."""
        result = UserService.get_all_users(db_session, skip=0, limit=1)
        assert len(result) <= 1


class TestGetUsersWithReputation:
    """Tests for UserService.get_users_with_reputation."""

    def test_get_users_with_reputation_empty(self, db_session: Session):
        """Should return empty list when no users match criteria."""
        result, total = UserService.get_users_with_reputation(
            db_session, page=100, page_size=10
        )
        assert result == []

    def test_get_users_with_reputation(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should return users with reputation data."""
        result, total = UserService.get_users_with_reputation(db_session)

        assert total >= 1
        assert len(result) >= 1
        assert "vote_score" in result[0]
        assert "penalty_count" in result[0]

    def test_get_users_with_reputation_search(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should filter by search term."""
        result, total = UserService.get_users_with_reputation(
            db_session, search=test_user.username
        )

        assert total >= 1
        assert any(u["username"] == test_user.username for u in result)

    def test_get_users_with_reputation_exclude_inactive(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should exclude inactive users."""
        result, total = UserService.get_users_with_reputation(
            db_session, include_inactive=False
        )

        assert all(u["is_active"] for u in result)


class TestGetUserById:
    """Tests for UserService.get_user_by_id."""

    def test_get_user_by_id_found(self, db_session: Session, test_user: db_models.User):
        """Should return user when found."""
        result = UserService.get_user_by_id(db_session, test_user.id)
        assert result is not None
        assert result.id == test_user.id

    def test_get_user_by_id_not_found(self, db_session: Session):
        """Should return None when not found."""
        result = UserService.get_user_by_id(db_session, 99999)
        assert result is None


class TestGetUserByIdOrRaise:
    """Tests for UserService.get_user_by_id_or_raise."""

    def test_get_user_by_id_or_raise_found(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should return user when found."""
        result = UserService.get_user_by_id_or_raise(db_session, test_user.id)
        assert result.id == test_user.id

    def test_get_user_by_id_or_raise_not_found(self, db_session: Session):
        """Should raise NotFoundException when not found."""
        with pytest.raises(NotFoundException):
            UserService.get_user_by_id_or_raise(db_session, 99999)


class TestGetUserByEmail:
    """Tests for UserService.get_user_by_email."""

    def test_get_user_by_email_found(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should return user when found."""
        result = UserService.get_user_by_email(db_session, test_user.email)
        assert result is not None
        assert result.email == test_user.email

    def test_get_user_by_email_not_found(self, db_session: Session):
        """Should return None when not found."""
        result = UserService.get_user_by_email(db_session, "notfound@test.com")
        assert result is None


class TestUpdateUser:
    """Tests for UserService.update_user."""

    def test_update_user(self, db_session: Session):
        """Should update user fields."""
        # Create a fresh user for this test
        user = db_models.User(
            email="updatetest@test.com",
            username="updatetest",
            display_name="Original Name",
            hashed_password="hash",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        # UserUpdate only supports is_active and is_global_admin
        update_data = schemas.UserUpdate(is_active=False)
        result = UserService.update_user(db_session, user.id, update_data)

        assert result.is_active is False

    def test_update_user_not_found(self, db_session: Session):
        """Should raise NotFoundException when user not found."""
        update_data = schemas.UserUpdate(is_active=False)

        with pytest.raises(NotFoundException):
            UserService.update_user(db_session, 99999, update_data)


class TestDeleteUser:
    """Tests for UserService.delete_user."""

    def test_delete_user(self, db_session: Session):
        """Should delete user and associated data."""
        # Create user to delete
        user = db_models.User(
            email="todelete@test.com",
            username="todelete",
            display_name="ToDelete",
            hashed_password="hash",
        )
        db_session.add(user)
        db_session.commit()
        user_id = user.id

        result = UserService.delete_user(db_session, user_id)

        assert result is True
        assert UserService.get_user_by_id(db_session, user_id) is None

    def test_delete_user_not_found(self, db_session: Session):
        """Should raise NotFoundException when user not found."""
        with pytest.raises(NotFoundException):
            UserService.delete_user(db_session, 99999)

    def test_delete_user_self_deletion(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should raise ValidationException for self-deletion."""
        with pytest.raises(ValidationException) as exc_info:
            UserService.delete_user(
                db_session, test_user.id, requesting_user_id=test_user.id
            )

        assert "Cannot delete your own account" in str(exc_info.value)


class TestAssignAdminRole:
    """Tests for UserService.assign_admin_role."""

    def test_assign_admin_role_category(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should assign category admin role."""
        result = UserService.assign_admin_role(
            db_session, test_user.id, test_category.id
        )

        assert result.user_id == test_user.id
        assert result.category_id == test_category.id

    def test_assign_admin_role_user_not_found(
        self, db_session: Session, test_category: db_models.Category
    ):
        """Should raise NotFoundException for non-existent user."""
        with pytest.raises(NotFoundException) as exc_info:
            UserService.assign_admin_role(db_session, 99999, test_category.id)

        assert "User not found" in str(exc_info.value)

    def test_assign_admin_role_category_not_found(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should raise NotFoundException for non-existent category."""
        with pytest.raises(NotFoundException) as exc_info:
            UserService.assign_admin_role(db_session, test_user.id, 99999)

        assert "Category not found" in str(exc_info.value)

    def test_assign_admin_role_duplicate(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should raise ValidationException for duplicate role."""
        # First assignment
        UserService.assign_admin_role(db_session, test_user.id, test_category.id)

        # Duplicate
        with pytest.raises(ValidationException) as exc_info:
            UserService.assign_admin_role(db_session, test_user.id, test_category.id)

        assert "already exists" in str(exc_info.value)


class TestRemoveAdminRole:
    """Tests for UserService.remove_admin_role."""

    def test_remove_admin_role(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should remove admin role."""
        # First create role
        UserService.assign_admin_role(db_session, test_user.id, test_category.id)

        # Then remove
        result = UserService.remove_admin_role(
            db_session, test_user.id, test_category.id
        )

        assert result is True

    def test_remove_admin_role_not_found(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should raise NotFoundException when role not found."""
        with pytest.raises(NotFoundException):
            UserService.remove_admin_role(db_session, test_user.id, test_category.id)


class TestGetUserAdminRoles:
    """Tests for UserService.get_user_admin_roles."""

    def test_get_user_admin_roles_empty(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should return empty list when no roles."""
        result = UserService.get_user_admin_roles(db_session, test_user.id)
        assert result == []

    def test_get_user_admin_roles(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should return admin roles for user."""
        UserService.assign_admin_role(db_session, test_user.id, test_category.id)

        result = UserService.get_user_admin_roles(db_session, test_user.id)

        assert len(result) == 1


class TestIsGlobalAdmin:
    """Tests for UserService.is_global_admin."""

    def test_is_global_admin_true(
        self, db_session: Session, admin_user: db_models.User
    ):
        """Should return True for global admin."""
        result = UserService.is_global_admin(db_session, admin_user.id)
        assert result is True

    def test_is_global_admin_false(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should return False for non-admin."""
        result = UserService.is_global_admin(db_session, test_user.id)
        assert result is False

    def test_is_global_admin_user_not_found(self, db_session: Session):
        """Should return False for non-existent user."""
        result = UserService.is_global_admin(db_session, 99999)
        assert result is False


class TestIsCategoryAdmin:
    """Tests for UserService.is_category_admin."""

    def test_is_category_admin_global_admin(
        self,
        db_session: Session,
        admin_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should return True for global admin on any category."""
        result = UserService.is_category_admin(
            db_session, admin_user.id, test_category.id
        )
        assert result is True

    def test_is_category_admin_with_role(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should return True for category admin."""
        UserService.assign_admin_role(db_session, test_user.id, test_category.id)

        result = UserService.is_category_admin(
            db_session, test_user.id, test_category.id
        )
        assert result is True

    def test_is_category_admin_no_role(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ):
        """Should return False without role."""
        result = UserService.is_category_admin(
            db_session, test_user.id, test_category.id
        )
        assert result is False


class TestGetUserStatistics:
    """Tests for UserService.get_user_statistics."""

    def test_get_user_statistics(self, db_session: Session, test_user: db_models.User):
        """Should return user statistics."""
        result = UserService.get_user_statistics(db_session, test_user.id)

        assert result.user_id == test_user.id
        assert result.ideas is not None
        assert result.votes_cast is not None
        assert result.votes_received is not None
        assert result.moderation is not None

    def test_get_user_statistics_with_data(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_idea: db_models.Idea,
    ):
        """Should include accurate stats with data."""
        # Add a vote
        vote = db_models.Vote(
            idea_id=test_idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.commit()

        result = UserService.get_user_statistics(db_session, test_user.id)

        assert result.votes_cast.total >= 1

    def test_get_user_statistics_not_found(self, db_session: Session):
        """Should raise NotFoundException for non-existent user."""
        with pytest.raises(NotFoundException):
            UserService.get_user_statistics(db_session, 99999)


class TestRegisterUser:
    """Tests for UserService.register_user."""

    def test_register_user(self, db_session: Session):
        """Should register new user."""
        user_data = schemas.UserCreate(
            email="newuser@test.com",
            username="newuser",
            display_name="New User",
            password="SecurePass123!",
            accepts_terms=True,
            accepts_privacy_policy=True,
        )

        result = UserService.register_user(db_session, user_data)

        assert result.email == "newuser@test.com"
        assert result.username == "newuser"

    def test_register_user_weak_password(self, db_session: Session):
        """Should reject weak password."""
        user_data = schemas.UserCreate(
            email="weak@test.com",
            username="weakpass",
            display_name="Weak",
            password="weak",
            accepts_terms=True,
            accepts_privacy_policy=True,
        )

        with pytest.raises(ValidationException):
            UserService.register_user(db_session, user_data)

    def test_register_user_duplicate_email(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should reject duplicate email."""
        user_data = schemas.UserCreate(
            email=test_user.email,
            username="unique",
            display_name="Unique",
            password="SecurePass123!",
            accepts_terms=True,
            accepts_privacy_policy=True,
        )

        with pytest.raises(ValidationException) as exc_info:
            UserService.register_user(db_session, user_data)

        assert "Email already registered" in str(exc_info.value)

    def test_register_user_duplicate_username(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should reject duplicate username."""
        user_data = schemas.UserCreate(
            email="unique@test.com",
            username=test_user.username,
            display_name="Unique",
            password="SecurePass123!",
            accepts_terms=True,
            accepts_privacy_policy=True,
        )

        with pytest.raises(ValidationException) as exc_info:
            UserService.register_user(db_session, user_data)

        assert "Username already taken" in str(exc_info.value)


class TestUpdateProfile:
    """Tests for UserService.update_profile."""

    def test_update_profile(self, db_session: Session, test_user: db_models.User):
        """Should update profile."""
        update_data = schemas.UserProfileUpdate(display_name="New Display Name")

        result = UserService.update_profile(db_session, test_user.id, update_data)

        assert result.display_name == "New Display Name"

    def test_update_profile_not_found(self, db_session: Session):
        """Should raise NotFoundException for non-existent user."""
        update_data = schemas.UserProfileUpdate(display_name="Updated")

        with pytest.raises(NotFoundException):
            UserService.update_profile(db_session, 99999, update_data)

    def test_update_profile_email_taken(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should reject duplicate email."""
        # Create another user
        other_user = db_models.User(
            email="other@test.com",
            username="other",
            display_name="Other",
            hashed_password="hash",
        )
        db_session.add(other_user)
        db_session.commit()

        update_data = schemas.UserProfileUpdate(email="other@test.com")

        with pytest.raises(ValidationException) as exc_info:
            UserService.update_profile(db_session, test_user.id, update_data)

        assert "Email already in use" in str(exc_info.value)


class TestChangePassword:
    """Tests for UserService.change_password."""

    def test_change_password(self, db_session: Session):
        """Should change password."""
        # Create user with known password (12+ chars required)
        from authentication.auth import get_password_hash

        user = db_models.User(
            email="passchange@test.com",
            username="passchange",
            display_name="PassChange",
            hashed_password=get_password_hash("OldSecurePass123!"),
        )
        db_session.add(user)
        db_session.commit()

        result = UserService.change_password(
            db_session, user.id, "OldSecurePass123!", "NewSecurePass456!"
        )

        assert result is True

    def test_change_password_not_found(self, db_session: Session):
        """Should raise NotFoundException for non-existent user."""
        with pytest.raises(NotFoundException):
            UserService.change_password(db_session, 99999, "old", "new")

    def test_change_password_wrong_current(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should reject wrong current password."""
        with pytest.raises(ValidationException) as exc_info:
            UserService.change_password(
                db_session, test_user.id, "WrongPassword!", "NewPass123!"
            )

        assert "Current password is incorrect" in str(exc_info.value)

    def test_change_password_weak_new(self, db_session: Session):
        """Should reject weak new password."""
        from authentication.auth import get_password_hash

        user = db_models.User(
            email="weaknew@test.com",
            username="weaknew",
            display_name="WeakNew",
            hashed_password=get_password_hash("OldSecurePass123!"),
        )
        db_session.add(user)
        db_session.commit()

        with pytest.raises(ValidationException):
            UserService.change_password(
                db_session, user.id, "OldSecurePass123!", "weak"
            )


class TestGetActivityHistory:
    """Tests for UserService.get_activity_history."""

    def test_get_activity_history(self, db_session: Session, test_user: db_models.User):
        """Should return activity history."""
        result = UserService.get_activity_history(db_session, test_user.id)

        assert result.ideas_count >= 0
        assert result.votes_count >= 0
        assert result.comments_count >= 0

    def test_get_activity_history_with_data(
        self,
        db_session: Session,
        test_user: db_models.User,
        test_idea: db_models.Idea,
    ):
        """Should include recent items."""
        # Add a comment
        comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment for activity history",
        )
        db_session.add(comment)
        db_session.commit()

        result = UserService.get_activity_history(db_session, test_user.id)

        assert result.comments_count >= 1
        assert len(result.recent_comments) >= 1

    def test_get_activity_history_not_found(self, db_session: Session):
        """Should raise NotFoundException for non-existent user."""
        with pytest.raises(NotFoundException):
            UserService.get_activity_history(db_session, 99999)


class TestUploadAvatar:
    """Tests for UserService.upload_avatar."""

    def test_upload_avatar_not_found(self, db_session: Session):
        """Should raise NotFoundException for non-existent user."""
        mock_file = MagicMock()
        mock_file.file.read.return_value = b"fake image content"

        with pytest.raises(NotFoundException):
            UserService.upload_avatar(db_session, 99999, mock_file)

    def test_upload_avatar_too_large(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should reject file exceeding size limit."""
        mock_file = MagicMock()
        # 6MB file
        mock_file.file.read.return_value = b"x" * (6 * 1024 * 1024)

        with pytest.raises(ValidationException) as exc_info:
            UserService.upload_avatar(db_session, test_user.id, mock_file)

        assert "5MB limit" in str(exc_info.value)

    @patch.dict("sys.modules", {"magic": MagicMock()})
    def test_upload_avatar_invalid_type(
        self, db_session: Session, test_user: db_models.User
    ):
        """Should reject invalid file type."""
        import sys

        sys.modules["magic"].from_buffer.return_value = "text/plain"

        mock_file = MagicMock()
        mock_file.file.read.return_value = b"not an image"

        with pytest.raises(ValidationException) as exc_info:
            UserService.upload_avatar(db_session, test_user.id, mock_file)

        assert "Invalid file type" in str(exc_info.value)

    @patch.dict("sys.modules", {"magic": MagicMock()})
    @patch("builtins.open", create=True)
    @patch("pathlib.Path.mkdir")
    def test_upload_avatar_success(
        self,
        mock_mkdir,
        mock_open,
        db_session: Session,
        test_user: db_models.User,
    ):
        """Should upload avatar successfully."""
        import sys

        sys.modules["magic"].from_buffer.return_value = "image/jpeg"

        mock_file = MagicMock()
        mock_file.file.read.return_value = b"fake jpeg content"

        result = UserService.upload_avatar(db_session, test_user.id, mock_file)

        assert result.message == "Avatar uploaded successfully"
        assert result.avatar_url is not None
