"""Tests for OfficialService."""

from datetime import datetime, timezone

import pytest

from models.exceptions import (
    BusinessRuleException,
    InsufficientPermissionsException,
    NotFoundException,
)
from services.official_service import OfficialService
import repositories.db_models as db_models
from authentication.auth import get_password_hash


@pytest.fixture
def official_user(db_session) -> db_models.User:
    """Create a user with official status."""
    user = db_models.User(
        email="official@example.com",
        username="officialuser",
        display_name="Official User",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        is_global_admin=False,
        is_official=True,
        official_title="City Planner",
        official_verified_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def requesting_user(db_session) -> db_models.User:
    """Create a user who requested official status."""
    user = db_models.User(
        email="requesting@example.com",
        username="requestinguser",
        display_name="Requesting User",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        is_global_admin=False,
        requests_official_status=True,
        official_title_request="Community Leader",
        official_request_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestGrantOfficialStatus:
    """Tests for grant_official_status."""

    def test_grant_official_status_success(self, db_session, test_user, admin_user):
        """Test granting official status to a user."""
        result = OfficialService.grant_official_status(
            db_session,
            user_id=test_user.id,
            official_title="Urban Planner",
            granted_by=admin_user,
        )

        assert result.is_official is True
        assert result.official_title == "Urban Planner"
        assert result.official_verified_at is not None

    def test_grant_official_status_without_title(
        self, db_session, test_user, admin_user
    ):
        """Test granting official status without a title."""
        result = OfficialService.grant_official_status(
            db_session,
            user_id=test_user.id,
            granted_by=admin_user,
        )

        assert result.is_official is True
        assert result.official_title is None

    def test_grant_clears_request_fields(self, db_session, requesting_user, admin_user):
        """Test that granting clears the request fields."""
        result = OfficialService.grant_official_status(
            db_session,
            user_id=requesting_user.id,
            official_title="Approved Title",
            granted_by=admin_user,
        )

        assert result.is_official is True
        assert result.official_title == "Approved Title"
        assert result.requests_official_status is False
        assert result.official_title_request is None
        assert result.official_request_at is None

    def test_grant_raises_if_not_admin(self, db_session, test_user, other_user):
        """Test that non-admins cannot grant official status."""
        with pytest.raises(InsufficientPermissionsException):
            OfficialService.grant_official_status(
                db_session,
                user_id=test_user.id,
                granted_by=other_user,
            )

    def test_grant_raises_if_user_not_found(self, db_session, admin_user):
        """Test that granting to non-existent user raises."""
        with pytest.raises(NotFoundException):
            OfficialService.grant_official_status(
                db_session,
                user_id=99999,
                granted_by=admin_user,
            )

    def test_grant_raises_if_already_official(
        self, db_session, official_user, admin_user
    ):
        """Test that granting to already official user raises."""
        with pytest.raises(BusinessRuleException):
            OfficialService.grant_official_status(
                db_session,
                user_id=official_user.id,
                granted_by=admin_user,
            )


class TestRevokeOfficialStatus:
    """Tests for revoke_official_status."""

    def test_revoke_official_status_success(
        self, db_session, official_user, admin_user
    ):
        """Test revoking official status."""
        result = OfficialService.revoke_official_status(
            db_session,
            user_id=official_user.id,
            revoked_by=admin_user,
        )

        assert result.is_official is False
        assert result.official_title is None
        assert result.official_verified_at is None

    def test_revoke_raises_if_not_admin(self, db_session, official_user, other_user):
        """Test that non-admins cannot revoke official status."""
        with pytest.raises(InsufficientPermissionsException):
            OfficialService.revoke_official_status(
                db_session,
                user_id=official_user.id,
                revoked_by=other_user,
            )

    def test_revoke_raises_if_user_not_found(self, db_session, admin_user):
        """Test that revoking from non-existent user raises."""
        with pytest.raises(NotFoundException):
            OfficialService.revoke_official_status(
                db_session,
                user_id=99999,
                revoked_by=admin_user,
            )

    def test_revoke_raises_if_not_official(self, db_session, test_user, admin_user):
        """Test that revoking from non-official user raises."""
        with pytest.raises(BusinessRuleException):
            OfficialService.revoke_official_status(
                db_session,
                user_id=test_user.id,
                revoked_by=admin_user,
            )


class TestUpdateOfficialTitle:
    """Tests for update_official_title."""

    def test_update_title_success(self, db_session, official_user, admin_user):
        """Test updating an official's title."""
        result = OfficialService.update_official_title(
            db_session,
            user_id=official_user.id,
            official_title="Senior City Planner",
            updated_by=admin_user,
        )

        assert result.official_title == "Senior City Planner"

    def test_update_raises_if_not_admin(self, db_session, official_user, other_user):
        """Test that non-admins cannot update titles."""
        with pytest.raises(InsufficientPermissionsException):
            OfficialService.update_official_title(
                db_session,
                user_id=official_user.id,
                official_title="New Title",
                updated_by=other_user,
            )

    def test_update_raises_if_user_not_found(self, db_session, admin_user):
        """Test that updating non-existent user raises."""
        with pytest.raises(NotFoundException):
            OfficialService.update_official_title(
                db_session,
                user_id=99999,
                official_title="New Title",
                updated_by=admin_user,
            )

    def test_update_raises_if_not_official(self, db_session, test_user, admin_user):
        """Test that updating non-official user raises."""
        with pytest.raises(BusinessRuleException):
            OfficialService.update_official_title(
                db_session,
                user_id=test_user.id,
                official_title="New Title",
                updated_by=admin_user,
            )


class TestGetAllOfficials:
    """Tests for get_all_officials."""

    def test_get_all_officials_success(self, db_session, official_user):
        """Test getting all officials."""
        officials = OfficialService.get_all_officials(db_session)

        assert len(officials) == 1
        assert officials[0].id == official_user.id

    def test_get_all_officials_excludes_inactive(self, db_session, official_user):
        """Test that inactive officials are excluded."""
        official_user.is_active = False
        db_session.commit()

        officials = OfficialService.get_all_officials(db_session)

        assert len(officials) == 0

    def test_get_all_officials_empty(self, db_session, test_user):
        """Test getting officials when none exist."""
        officials = OfficialService.get_all_officials(db_session)

        assert len(officials) == 0


class TestGetPendingOfficialRequests:
    """Tests for get_pending_official_requests."""

    def test_get_pending_requests_success(self, db_session, requesting_user):
        """Test getting pending official requests."""
        requests = OfficialService.get_pending_official_requests(db_session)

        assert len(requests) == 1
        assert requests[0].id == requesting_user.id

    def test_get_pending_excludes_already_official(self, db_session, requesting_user):
        """Test that already official users are excluded."""
        requesting_user.is_official = True
        db_session.commit()

        requests = OfficialService.get_pending_official_requests(db_session)

        assert len(requests) == 0

    def test_get_pending_excludes_inactive(self, db_session, requesting_user):
        """Test that inactive users are excluded."""
        requesting_user.is_active = False
        db_session.commit()

        requests = OfficialService.get_pending_official_requests(db_session)

        assert len(requests) == 0


class TestRejectOfficialRequest:
    """Tests for reject_official_request."""

    def test_reject_request_success(self, db_session, requesting_user, admin_user):
        """Test rejecting an official request."""
        result = OfficialService.reject_official_request(
            db_session,
            user_id=requesting_user.id,
            rejected_by=admin_user,
        )

        assert result.requests_official_status is False
        assert result.official_title_request is None
        assert result.official_request_at is None

    def test_reject_raises_if_not_admin(self, db_session, requesting_user, other_user):
        """Test that non-admins cannot reject requests."""
        with pytest.raises(InsufficientPermissionsException):
            OfficialService.reject_official_request(
                db_session,
                user_id=requesting_user.id,
                rejected_by=other_user,
            )

    def test_reject_raises_if_user_not_found(self, db_session, admin_user):
        """Test that rejecting non-existent user raises."""
        with pytest.raises(NotFoundException):
            OfficialService.reject_official_request(
                db_session,
                user_id=99999,
                rejected_by=admin_user,
            )

    def test_reject_raises_if_no_request(self, db_session, test_user, admin_user):
        """Test that rejecting user without request raises."""
        with pytest.raises(BusinessRuleException):
            OfficialService.reject_official_request(
                db_session,
                user_id=test_user.id,
                rejected_by=admin_user,
            )


class TestIsOfficial:
    """Tests for is_official."""

    def test_is_official_true(self, db_session, official_user):
        """Test that is_official returns True for officials."""
        assert OfficialService.is_official(db_session, official_user.id) is True

    def test_is_official_false(self, db_session, test_user):
        """Test that is_official returns False for non-officials."""
        assert OfficialService.is_official(db_session, test_user.id) is False

    def test_is_official_nonexistent_user(self, db_session):
        """Test that is_official returns False for non-existent users."""
        assert OfficialService.is_official(db_session, 99999) is False


class TestTitleValidation:
    """Tests for official title validation (Phase 5)."""

    def test_grant_with_valid_title(self, db_session, test_user, admin_user):
        """Test granting with a valid title."""
        result = OfficialService.grant_official_status(
            db_session,
            user_id=test_user.id,
            official_title="Urban Planner (Downtown)",
            granted_by=admin_user,
        )
        assert result.official_title == "Urban Planner (Downtown)"

    def test_grant_with_unicode_title(self, db_session, test_user, admin_user):
        """Test granting with Unicode characters in title."""
        result = OfficialService.grant_official_status(
            db_session,
            user_id=test_user.id,
            official_title="Conseiller d'arrondissement",
            granted_by=admin_user,
        )
        assert result.official_title == "Conseiller d'arrondissement"

    def test_grant_with_title_too_long(self, db_session, test_user, admin_user):
        """Test that titles over 100 chars are rejected."""
        long_title = "A" * 101
        with pytest.raises(BusinessRuleException) as exc_info:
            OfficialService.grant_official_status(
                db_session,
                user_id=test_user.id,
                official_title=long_title,
                granted_by=admin_user,
            )
        assert "less than 100 characters" in str(exc_info.value)

    def test_grant_with_invalid_characters(self, db_session, test_user, admin_user):
        """Test that titles with invalid characters are rejected."""
        with pytest.raises(BusinessRuleException) as exc_info:
            OfficialService.grant_official_status(
                db_session,
                user_id=test_user.id,
                official_title="Title <script>alert('xss')</script>",
                granted_by=admin_user,
            )
        assert "invalid characters" in str(exc_info.value)

    def test_grant_with_empty_title_becomes_none(
        self, db_session, test_user, admin_user
    ):
        """Test that empty/whitespace title becomes None."""
        result = OfficialService.grant_official_status(
            db_session,
            user_id=test_user.id,
            official_title="   ",
            granted_by=admin_user,
        )
        assert result.official_title is None

    def test_grant_title_is_trimmed(self, db_session, test_user, admin_user):
        """Test that title is trimmed of whitespace."""
        result = OfficialService.grant_official_status(
            db_session,
            user_id=test_user.id,
            official_title="  City Planner  ",
            granted_by=admin_user,
        )
        assert result.official_title == "City Planner"

    def test_update_with_title_too_long(self, db_session, official_user, admin_user):
        """Test that updating with title over 100 chars is rejected."""
        long_title = "B" * 101
        with pytest.raises(BusinessRuleException) as exc_info:
            OfficialService.update_official_title(
                db_session,
                user_id=official_user.id,
                official_title=long_title,
                updated_by=admin_user,
            )
        assert "less than 100 characters" in str(exc_info.value)

    def test_update_with_invalid_characters(
        self, db_session, official_user, admin_user
    ):
        """Test that updating with invalid characters is rejected."""
        with pytest.raises(BusinessRuleException) as exc_info:
            OfficialService.update_official_title(
                db_session,
                user_id=official_user.id,
                official_title="Title with @#$% symbols",
                updated_by=admin_user,
            )
        assert "invalid characters" in str(exc_info.value)
