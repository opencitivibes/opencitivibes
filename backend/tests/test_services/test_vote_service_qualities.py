"""
Unit tests for VoteService quality handling.
"""

import pytest
from sqlalchemy.orm import Session

from models.exceptions import BusinessRuleException, VoteNotFoundException
from repositories.db_models import (
    Idea,
    Quality,
    User,
    Vote,
    VoteQuality,
    VoteType,
)
from services.vote_service import VoteService


@pytest.fixture
def test_quality(db_session: Session) -> Quality:
    """Create a test quality."""
    quality = Quality(
        key="test_benefit",
        name_en="Test Benefit",
        name_fr="Bénéfice Test",
        is_default=True,
        is_active=True,
        display_order=1,
    )
    db_session.add(quality)
    db_session.commit()
    db_session.refresh(quality)
    return quality


@pytest.fixture
def other_quality(db_session: Session) -> Quality:
    """Create another test quality."""
    quality = Quality(
        key="other_benefit",
        name_en="Other Benefit",
        name_fr="Autre Bénéfice",
        is_default=True,
        is_active=True,
        display_order=2,
    )
    db_session.add(quality)
    db_session.commit()
    db_session.refresh(quality)
    return quality


class TestVoteOnIdeaWithQualities:
    """Tests for vote_on_idea with quality_ids parameter."""

    def test_upvote_with_qualities(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
    ):
        """Should attach qualities to upvote."""
        vote = VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.UPVOTE,
            quality_ids=[test_quality.id],
        )

        assert vote.vote_type == VoteType.UPVOTE

        # Verify qualities are attached
        vote_qualities = (
            db_session.query(VoteQuality).filter(VoteQuality.vote_id == vote.id).all()
        )
        assert len(vote_qualities) == 1
        assert vote_qualities[0].quality_id == test_quality.id

    def test_upvote_with_multiple_qualities(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
        other_quality: Quality,
    ):
        """Should attach multiple qualities to upvote."""
        vote = VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.UPVOTE,
            quality_ids=[test_quality.id, other_quality.id],
        )

        vote_qualities = (
            db_session.query(VoteQuality).filter(VoteQuality.vote_id == vote.id).all()
        )
        assert len(vote_qualities) == 2

    def test_downvote_ignores_qualities(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
    ):
        """Should ignore qualities for downvotes."""
        vote = VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.DOWNVOTE,
            quality_ids=[test_quality.id],
        )

        assert vote.vote_type == VoteType.DOWNVOTE

        # Verify no qualities attached
        vote_qualities = (
            db_session.query(VoteQuality).filter(VoteQuality.vote_id == vote.id).all()
        )
        assert len(vote_qualities) == 0

    def test_upvote_without_qualities(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
    ):
        """Should work without quality_ids parameter."""
        vote = VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.UPVOTE,
        )

        assert vote.vote_type == VoteType.UPVOTE
        vote_qualities = (
            db_session.query(VoteQuality).filter(VoteQuality.vote_id == vote.id).all()
        )
        assert len(vote_qualities) == 0

    def test_switch_to_downvote_clears_qualities(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
    ):
        """Should clear qualities when switching from upvote to downvote."""
        # First upvote with quality
        VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.UPVOTE,
            quality_ids=[test_quality.id],
        )

        # Switch to downvote
        vote = VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.DOWNVOTE,
        )

        # Qualities should be cleared
        vote_qualities = (
            db_session.query(VoteQuality).filter(VoteQuality.vote_id == vote.id).all()
        )
        assert len(vote_qualities) == 0

    def test_update_existing_upvote_with_new_qualities(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
        other_quality: Quality,
    ):
        """Should replace qualities when updating existing upvote."""
        # First upvote with one quality
        VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.UPVOTE,
            quality_ids=[test_quality.id],
        )

        # Update with different quality
        vote = VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.UPVOTE,
            quality_ids=[other_quality.id],
        )

        vote_qualities = (
            db_session.query(VoteQuality).filter(VoteQuality.vote_id == vote.id).all()
        )
        assert len(vote_qualities) == 1
        assert vote_qualities[0].quality_id == other_quality.id

    def test_filters_invalid_quality_ids(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
    ):
        """Should filter out invalid quality IDs silently."""
        vote = VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.UPVOTE,
            quality_ids=[test_quality.id, 9999],  # 9999 is invalid
        )

        vote_qualities = (
            db_session.query(VoteQuality).filter(VoteQuality.vote_id == vote.id).all()
        )
        # Only valid quality should be attached
        assert len(vote_qualities) == 1
        assert vote_qualities[0].quality_id == test_quality.id


class TestUpdateVoteQualities:
    """Tests for update_vote_qualities method."""

    def test_updates_qualities_on_existing_upvote(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
        other_quality: Quality,
    ):
        """Should update qualities on existing upvote."""
        # Create upvote first
        VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.UPVOTE,
        )

        # Update qualities
        result = VoteService.update_vote_qualities(
            db_session,
            test_idea.id,
            other_user.id,
            [test_quality.id, other_quality.id],
        )

        assert len(result) == 2
        assert test_quality.id in result
        assert other_quality.id in result

    def test_raises_for_no_vote(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
    ):
        """Should raise VoteNotFoundException when no vote exists."""
        with pytest.raises(VoteNotFoundException):
            VoteService.update_vote_qualities(
                db_session,
                test_idea.id,
                other_user.id,
                [test_quality.id],
            )

    def test_raises_for_downvote(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
    ):
        """Should raise BusinessRuleException for downvote."""
        # Create downvote
        VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.DOWNVOTE,
        )

        with pytest.raises(BusinessRuleException) as exc_info:
            VoteService.update_vote_qualities(
                db_session,
                test_idea.id,
                other_user.id,
                [test_quality.id],
            )
        assert "upvotes" in str(exc_info.value).lower()


class TestGetVoteQualities:
    """Tests for get_vote_qualities method."""

    def test_returns_quality_ids(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
    ):
        """Should return quality IDs for upvote."""
        VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.UPVOTE,
            quality_ids=[test_quality.id],
        )

        result = VoteService.get_vote_qualities(db_session, test_idea.id, other_user.id)

        assert result == [test_quality.id]

    def test_returns_empty_for_no_vote(
        self, db_session: Session, test_idea: Idea, other_user: User
    ):
        """Should return empty list when no vote exists."""
        result = VoteService.get_vote_qualities(db_session, test_idea.id, other_user.id)

        assert result == []

    def test_returns_empty_for_downvote(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
    ):
        """Should return empty list for downvote."""
        VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.DOWNVOTE,
        )

        result = VoteService.get_vote_qualities(db_session, test_idea.id, other_user.id)

        assert result == []

    def test_returns_empty_for_upvote_without_qualities(
        self, db_session: Session, test_idea: Idea, other_user: User
    ):
        """Should return empty list for upvote without qualities."""
        VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.UPVOTE,
        )

        result = VoteService.get_vote_qualities(db_session, test_idea.id, other_user.id)

        assert result == []


class TestRemoveVoteWithQualities:
    """Tests for remove_vote with qualities cleanup."""

    def test_removes_vote_and_qualities(
        self,
        db_session: Session,
        test_idea: Idea,
        other_user: User,
        test_quality: Quality,
    ):
        """Should remove vote and associated qualities."""
        # Create vote with quality
        vote = VoteService.vote_on_idea(
            db_session,
            test_idea.id,
            other_user.id,
            VoteType.UPVOTE,
            quality_ids=[test_quality.id],
        )
        vote_id = vote.id

        # Remove vote
        VoteService.remove_vote(db_session, test_idea.id, other_user.id)

        # Verify vote and qualities are gone
        assert db_session.query(Vote).filter(Vote.id == vote_id).first() is None
        assert (
            db_session.query(VoteQuality).filter(VoteQuality.vote_id == vote_id).first()
            is None
        )
