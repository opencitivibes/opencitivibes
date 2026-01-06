"""
Tests for the edit approved ideas workflow.

Tests cover:
- Edit rate limiting (max 3 edits/month/idea)
- Cool-down period (24 hours between edits)
- Status transitions (APPROVED → PENDING_EDIT → APPROVED/REJECTED)
- Vote/comment preservation during re-moderation
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

import models.schemas as schemas
import repositories.db_models as db_models
from models.exceptions import (
    CannotEditIdeaException,
    EditCooldownException,
    EditRateLimitException,
    NotFoundException,
    PermissionDeniedException,
)
from repositories.idea_repository import IdeaRepository
from services.idea_service import IdeaService


class TestEditApprovedIdeas:
    """Tests for editing approved ideas with re-moderation."""

    @pytest.fixture
    def approved_idea(
        self, db: Session, test_user: db_models.User, test_category: db_models.Category
    ) -> db_models.Idea:
        """Create an approved idea for testing."""
        idea = db_models.Idea(
            title="Test Approved Idea",
            description="This is an approved test idea",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
            validated_at=datetime.now(timezone.utc),
            language="en",
        )
        db.add(idea)
        db.commit()
        db.refresh(idea)
        return idea

    def test_edit_approved_idea_transitions_to_pending_edit(
        self, db: Session, approved_idea: db_models.Idea, test_user: db_models.User
    ):
        """Editing an approved idea should transition it to PENDING_EDIT status."""
        update = schemas.IdeaUpdate(title="Updated Title")

        updated_idea = IdeaService.update_idea(
            db, approved_idea.id, update, test_user.id
        )

        assert updated_idea.status == db_models.IdeaStatus.PENDING_EDIT
        assert updated_idea.previous_status == "approved"
        assert updated_idea.edit_count == 1
        assert updated_idea.last_edit_at is not None
        assert updated_idea.title == "Updated Title"

    def test_edit_approved_idea_preserves_previous_status(
        self, db: Session, approved_idea: db_models.Idea, test_user: db_models.User
    ):
        """Previous status should be stored for restoration after approval."""
        update = schemas.IdeaUpdate(description="Updated description")

        updated_idea = IdeaService.update_idea(
            db, approved_idea.id, update, test_user.id
        )

        assert updated_idea.previous_status == "approved"

    def test_cannot_edit_pending_edit_idea(
        self, db: Session, approved_idea: db_models.Idea, test_user: db_models.User
    ):
        """Cannot edit an idea that's already in PENDING_EDIT status."""
        # First edit to get to PENDING_EDIT
        approved_idea.status = db_models.IdeaStatus.PENDING_EDIT
        db.commit()

        update = schemas.IdeaUpdate(title="Another update")

        with pytest.raises(CannotEditIdeaException):
            IdeaService.update_idea(db, approved_idea.id, update, test_user.id)

    def test_edit_cooldown_enforced(
        self, db: Session, approved_idea: db_models.Idea, test_user: db_models.User
    ):
        """Must wait 24 hours between edits on approved ideas."""
        # Set last_edit_at to 12 hours ago (within cooldown)
        approved_idea.last_edit_at = datetime.now(timezone.utc) - timedelta(hours=12)
        approved_idea.edit_count = 1
        db.commit()

        update = schemas.IdeaUpdate(title="New title")

        with pytest.raises(EditCooldownException) as exc_info:
            IdeaService.update_idea(db, approved_idea.id, update, test_user.id)

        assert exc_info.value.retry_after_hours > 0
        assert exc_info.value.retry_after_hours <= 12

    def test_edit_cooldown_passed(
        self, db: Session, approved_idea: db_models.Idea, test_user: db_models.User
    ):
        """Can edit if 24 hours have passed since last edit."""
        # Set last_edit_at to 25 hours ago (past cooldown)
        approved_idea.last_edit_at = datetime.now(timezone.utc) - timedelta(hours=25)
        approved_idea.edit_count = 1
        db.commit()

        update = schemas.IdeaUpdate(title="New title after cooldown")

        # Should not raise
        updated_idea = IdeaService.update_idea(
            db, approved_idea.id, update, test_user.id
        )

        assert updated_idea.title == "New title after cooldown"
        assert updated_idea.edit_count == 2

    def test_edit_rate_limit_enforced(
        self, db: Session, approved_idea: db_models.Idea, test_user: db_models.User
    ):
        """Cannot exceed 3 edits per month per idea."""
        # Set edit_count to 3 (max), last_edit_at to this month
        approved_idea.last_edit_at = datetime.now(timezone.utc) - timedelta(hours=25)
        approved_idea.edit_count = 3
        db.commit()

        update = schemas.IdeaUpdate(title="Fourth edit attempt")

        with pytest.raises(EditRateLimitException) as exc_info:
            IdeaService.update_idea(db, approved_idea.id, update, test_user.id)

        assert exc_info.value.edits_this_month == 3
        assert exc_info.value.max_edits == 3

    def test_edit_rate_limit_resets_new_month(
        self, db: Session, approved_idea: db_models.Idea, test_user: db_models.User
    ):
        """Edit count should reset when a new month begins."""
        # Set last_edit_at to last month with 3 edits
        last_month = datetime.now(timezone.utc).replace(day=1) - timedelta(days=1)
        approved_idea.last_edit_at = last_month
        approved_idea.edit_count = 3
        db.commit()

        update = schemas.IdeaUpdate(title="First edit of new month")

        # Should not raise - new month resets the count
        updated_idea = IdeaService.update_idea(
            db, approved_idea.id, update, test_user.id
        )

        assert updated_idea.edit_count == 1
        assert updated_idea.title == "First edit of new month"

    def test_only_owner_can_edit(
        self,
        db: Session,
        approved_idea: db_models.Idea,
        test_user: db_models.User,
        other_user: db_models.User,
    ):
        """Only the idea owner can edit it."""
        update = schemas.IdeaUpdate(title="Hijack attempt")

        with pytest.raises(PermissionDeniedException):
            IdeaService.update_idea(db, approved_idea.id, update, other_user.id)


class TestModeratePendingEdit:
    """Tests for moderating ideas in PENDING_EDIT status."""

    @pytest.fixture
    def pending_edit_idea(
        self, db: Session, test_user: db_models.User, test_category: db_models.Category
    ) -> db_models.Idea:
        """Create a PENDING_EDIT idea for testing."""
        idea = db_models.Idea(
            title="Edited Idea",
            description="This was edited",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.PENDING_EDIT,
            previous_status="approved",
            edit_count=1,
            last_edit_at=datetime.now(timezone.utc),
            language="en",
        )
        db.add(idea)
        db.commit()
        db.refresh(idea)
        return idea

    def test_approve_pending_edit_restores_status(
        self, db: Session, pending_edit_idea: db_models.Idea
    ):
        """Approving a PENDING_EDIT idea should restore it to APPROVED."""
        moderation = schemas.IdeaModerate(
            status=db_models.IdeaStatus.APPROVED,
            admin_comment="Edit approved",
        )

        result = IdeaService.moderate_idea(db, pending_edit_idea.id, moderation)

        assert result.status == db_models.IdeaStatus.APPROVED
        assert result.previous_status is None  # Cleared after restoration
        assert result.admin_comment == "Edit approved"
        assert result.validated_at is not None

    def test_reject_pending_edit_sets_rejected(
        self, db: Session, pending_edit_idea: db_models.Idea
    ):
        """Rejecting a PENDING_EDIT idea should set it to REJECTED."""
        moderation = schemas.IdeaModerate(
            status=db_models.IdeaStatus.REJECTED,
            admin_comment="Edit contains inappropriate content",
        )

        result = IdeaService.moderate_idea(db, pending_edit_idea.id, moderation)

        assert result.status == db_models.IdeaStatus.REJECTED
        # Previous status preserved for history
        assert result.previous_status == "approved"
        assert result.admin_comment == "Edit contains inappropriate content"


class TestPendingEditVisibility:
    """Tests for visibility rules of PENDING_EDIT ideas."""

    @pytest.fixture
    def pending_edit_idea_with_votes(
        self, db: Session, test_user: db_models.User, test_category: db_models.Category
    ) -> db_models.Idea:
        """Create a PENDING_EDIT idea with votes for testing."""
        idea = db_models.Idea(
            title="Popular Edited Idea",
            description="This was edited after being popular",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.PENDING_EDIT,
            previous_status="approved",
            edit_count=1,
            last_edit_at=datetime.now(timezone.utc),
            language="en",
        )
        db.add(idea)
        db.commit()
        db.refresh(idea)

        # Add some votes
        for i in range(3):
            voter = db_models.User(
                email=f"voter{i}@test.com",
                username=f"voter{i}",
                display_name=f"Voter {i}",
                hashed_password="hashed",
                is_active=True,
            )
            db.add(voter)
            db.commit()

            vote = db_models.Vote(
                idea_id=idea.id,
                user_id=voter.id,
                vote_type=db_models.VoteType.UPVOTE,
            )
            db.add(vote)

        db.commit()
        db.refresh(idea)
        return idea

    def test_pending_edit_hidden_from_leaderboard(
        self, db: Session, pending_edit_idea_with_votes: db_models.Idea
    ):
        """PENDING_EDIT ideas should not appear in the public leaderboard."""
        ideas = IdeaService.get_leaderboard(db, skip=0, limit=100)

        idea_ids = [i.id for i in ideas]
        assert pending_edit_idea_with_votes.id not in idea_ids

    def test_owner_can_see_pending_edit_idea(
        self,
        db: Session,
        pending_edit_idea_with_votes: db_models.Idea,
        test_user: db_models.User,
    ):
        """Owner should be able to view their PENDING_EDIT idea."""
        idea = IdeaService.get_idea_with_score(
            db, pending_edit_idea_with_votes.id, test_user.id
        )

        assert idea is not None
        assert idea.id == pending_edit_idea_with_votes.id
        assert idea.status == db_models.IdeaStatus.PENDING_EDIT

    def test_non_owner_cannot_see_pending_edit_idea(
        self,
        db: Session,
        pending_edit_idea_with_votes: db_models.Idea,
        other_user: db_models.User,
    ):
        """Non-owner should not be able to view PENDING_EDIT idea."""
        with pytest.raises(NotFoundException):
            IdeaService.get_idea_with_score(
                db, pending_edit_idea_with_votes.id, other_user.id
            )

    def test_pending_edit_appears_in_my_ideas(
        self,
        db: Session,
        pending_edit_idea_with_votes: db_models.Idea,
        test_user: db_models.User,
    ):
        """PENDING_EDIT ideas should appear in owner's 'My Ideas' list."""
        my_ideas = IdeaService.get_my_ideas(db, test_user.id, skip=0, limit=100)

        idea_ids = [i.id for i in my_ideas]
        assert pending_edit_idea_with_votes.id in idea_ids


class TestEditTrackingRepository:
    """Tests for repository-level edit tracking methods."""

    def test_get_edit_count_this_month_returns_zero_for_never_edited(
        self, db: Session, test_user: db_models.User, test_category: db_models.Category
    ):
        """Returns 0 for ideas that have never been edited."""
        idea = db_models.Idea(
            title="Never Edited",
            description="Fresh idea",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
            language="en",
        )
        db.add(idea)
        db.commit()

        repo = IdeaRepository(db)
        count = repo.get_edit_count_this_month(idea.id)

        assert count == 0

    def test_get_edit_count_this_month_returns_count_for_current_month(
        self, db: Session, test_user: db_models.User, test_category: db_models.Category
    ):
        """Returns correct count for edits in the current month."""
        idea = db_models.Idea(
            title="Edited This Month",
            description="Recently edited",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
            edit_count=2,
            last_edit_at=datetime.now(timezone.utc),
            language="en",
        )
        db.add(idea)
        db.commit()

        repo = IdeaRepository(db)
        count = repo.get_edit_count_this_month(idea.id)

        assert count == 2

    def test_get_edit_count_this_month_returns_zero_for_last_month(
        self, db: Session, test_user: db_models.User, test_category: db_models.Category
    ):
        """Returns 0 if last edit was in a previous month (count resets)."""
        last_month = datetime.now(timezone.utc).replace(day=1) - timedelta(days=1)
        idea = db_models.Idea(
            title="Edited Last Month",
            description="Old edit",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
            edit_count=3,
            last_edit_at=last_month,
            language="en",
        )
        db.add(idea)
        db.commit()

        repo = IdeaRepository(db)
        count = repo.get_edit_count_this_month(idea.id)

        assert count == 0

    def test_get_pending_edits(
        self, db: Session, test_user: db_models.User, test_category: db_models.Category
    ):
        """Returns all ideas with PENDING_EDIT status."""
        # Create some PENDING_EDIT ideas
        for i in range(3):
            idea = db_models.Idea(
                title=f"Pending Edit {i}",
                description=f"Awaiting review {i}",
                category_id=test_category.id,
                user_id=test_user.id,
                status=db_models.IdeaStatus.PENDING_EDIT,
                last_edit_at=datetime.now(timezone.utc),
                language="en",
            )
            db.add(idea)

        # Create one APPROVED idea
        approved = db_models.Idea(
            title="Approved",
            description="This is approved",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
            language="en",
        )
        db.add(approved)
        db.commit()

        repo = IdeaRepository(db)
        pending_edits = repo.get_pending_edits()

        assert len(pending_edits) == 3
        assert all(i.status == db_models.IdeaStatus.PENDING_EDIT for i in pending_edits)

    def test_count_pending_edits(
        self, db: Session, test_user: db_models.User, test_category: db_models.Category
    ):
        """Counts ideas with PENDING_EDIT status."""
        for i in range(5):
            idea = db_models.Idea(
                title=f"Pending Edit Count {i}",
                description=f"Count test {i}",
                category_id=test_category.id,
                user_id=test_user.id,
                status=db_models.IdeaStatus.PENDING_EDIT,
                last_edit_at=datetime.now(timezone.utc),
                language="en",
            )
            db.add(idea)
        db.commit()

        repo = IdeaRepository(db)
        count = repo.count_pending_edits()

        assert count == 5
