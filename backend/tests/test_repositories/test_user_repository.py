"""Tests for UserRepository."""

import repositories.db_models as db_models
from repositories.user_repository import UserRepository
from authentication.auth import get_password_hash


class TestUserRepository:
    """Test cases for UserRepository."""

    def test_get_by_email_found(self, db_session, test_user):
        """Get user by email when user exists."""
        repo = UserRepository(db_session)
        user = repo.get_by_email(test_user.email)

        assert user is not None
        assert user.email == test_user.email
        assert user.id == test_user.id

    def test_get_by_email_not_found(self, db_session):
        """Get user by email returns None when not found."""
        repo = UserRepository(db_session)
        user = repo.get_by_email("nonexistent@example.com")
        assert user is None

    def test_get_by_username_found(self, db_session, test_user):
        """Get user by username when user exists."""
        repo = UserRepository(db_session)
        user = repo.get_by_username(test_user.username)

        assert user is not None
        assert user.username == test_user.username
        assert user.id == test_user.id

    def test_get_by_username_not_found(self, db_session):
        """Get user by username returns None when not found."""
        repo = UserRepository(db_session)
        user = repo.get_by_username("nonexistent")
        assert user is None

    def test_email_exists_true(self, db_session, test_user):
        """Email exists returns True for existing email."""
        repo = UserRepository(db_session)
        exists = repo.email_exists(test_user.email)
        assert exists is True

    def test_email_exists_false(self, db_session):
        """Email exists returns False for non-existent email."""
        repo = UserRepository(db_session)
        exists = repo.email_exists("nonexistent@example.com")
        assert exists is False

    def test_username_exists_true(self, db_session, test_user):
        """Username exists returns True for existing username."""
        repo = UserRepository(db_session)
        exists = repo.username_exists(test_user.username)
        assert exists is True

    def test_username_exists_false(self, db_session):
        """Username exists returns False for non-existent username."""
        repo = UserRepository(db_session)
        exists = repo.username_exists("nonexistent")
        assert exists is False

    def test_get_all_users(self, db_session, test_user, admin_user):
        """Get all users returns all users."""
        repo = UserRepository(db_session)
        users = repo.get_all_users()

        assert len(users) >= 2
        user_ids = [u.id for u in users]
        assert test_user.id in user_ids
        assert admin_user.id in user_ids

    def test_get_all_users_pagination(self, db_session, test_user, admin_user):
        """Get all users with pagination."""
        # Create additional users
        for i in range(5):
            user = db_models.User(
                email=f"user{i}@example.com",
                username=f"user{i}",
                display_name=f"User {i}",
                hashed_password=get_password_hash("password123"),
                is_active=True,
                is_global_admin=False,
            )
            db_session.add(user)
        db_session.commit()

        repo = UserRepository(db_session)

        # Test pagination
        page1 = repo.get_all_users(skip=0, limit=2)
        page2 = repo.get_all_users(skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    def test_delete_user_and_related_success(
        self, db_session, test_user, test_category
    ):
        """Delete user and all related records."""
        # Create related records
        idea = db_models.Idea(
            title="Test Idea",
            description="Test idea description that is long enough.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        db_session.add(idea)
        db_session.commit()

        vote = db_models.Vote(
            idea_id=idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote)

        comment = db_models.Comment(
            idea_id=idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)

        admin_role = db_models.AdminRole(
            user_id=test_user.id, category_id=test_category.id
        )
        db_session.add(admin_role)
        db_session.commit()

        user_id = test_user.id

        # Delete user
        repo = UserRepository(db_session)
        result = repo.delete_user_and_related(user_id)

        assert result is True

        # Verify user is deleted
        deleted_user = repo.get_by_id(user_id)
        assert deleted_user is None

        # Verify related records are deleted
        assert (
            db_session.query(db_models.Vote).filter_by(user_id=user_id).first() is None
        )
        assert (
            db_session.query(db_models.Comment).filter_by(user_id=user_id).first()
            is None
        )
        assert (
            db_session.query(db_models.AdminRole).filter_by(user_id=user_id).first()
            is None
        )
        assert (
            db_session.query(db_models.Idea).filter_by(user_id=user_id).first() is None
        )

    def test_delete_user_and_related_not_found(self, db_session):
        """Delete non-existent user returns False."""
        repo = UserRepository(db_session)
        result = repo.delete_user_and_related(99999)
        assert result is False

    def test_get_admin_roles(self, db_session, test_user, test_category):
        """Get admin roles for a user."""
        # Create admin roles
        role1 = db_models.AdminRole(user_id=test_user.id, category_id=test_category.id)
        db_session.add(role1)
        db_session.commit()

        repo = UserRepository(db_session)
        roles = repo.get_admin_roles(test_user.id)

        assert len(roles) == 1
        assert roles[0].user_id == test_user.id
        assert roles[0].category_id == test_category.id

    def test_has_admin_permission_global_admin(self, db_session, admin_user):
        """Global admin has permission for any category."""
        repo = UserRepository(db_session)

        # Should return True for global admin
        assert repo.has_admin_permission(admin_user.id) is True
        assert repo.has_admin_permission(admin_user.id, category_id=1) is True

    def test_has_admin_permission_category_admin(
        self, db_session, test_user, test_category
    ):
        """Category admin has permission for specific category."""
        # Create category admin role
        role = db_models.AdminRole(user_id=test_user.id, category_id=test_category.id)
        db_session.add(role)
        db_session.commit()

        repo = UserRepository(db_session)

        # Should have permission for their category
        assert repo.has_admin_permission(test_user.id, test_category.id) is True

        # Should not have global permission
        assert repo.has_admin_permission(test_user.id) is False

    def test_has_admin_permission_no_permission(self, db_session, test_user):
        """Regular user has no admin permission."""
        repo = UserRepository(db_session)

        assert repo.has_admin_permission(test_user.id) is False
        assert repo.has_admin_permission(test_user.id, category_id=1) is False

    def test_has_admin_permission_user_not_found(self, db_session):
        """Has admin permission returns False for non-existent user."""
        repo = UserRepository(db_session)
        assert repo.has_admin_permission(99999) is False
