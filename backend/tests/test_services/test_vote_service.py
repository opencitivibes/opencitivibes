"""Tests for VoteService."""

import pytest

import repositories.db_models as db_models
from models.exceptions import (
    BusinessRuleException,
    IdeaNotFoundException,
    VoteNotFoundException,
)
from services.vote_service import VoteService


class TestVoteService:
    """Test cases for vote operations."""

    def test_vote_on_idea_upvote_success(self, db_session, other_user, test_idea):
        """User can upvote an approved idea (not their own)."""
        result = VoteService.vote_on_idea(
            db=db_session,
            idea_id=test_idea.id,
            user_id=other_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )

        assert result is not None
        assert result.idea_id == test_idea.id
        assert result.user_id == other_user.id
        assert result.vote_type == db_models.VoteType.UPVOTE

    def test_vote_on_idea_downvote_success(self, db_session, other_user, test_idea):
        """User can downvote an approved idea (not their own)."""
        result = VoteService.vote_on_idea(
            db=db_session,
            idea_id=test_idea.id,
            user_id=other_user.id,
            vote_type=db_models.VoteType.DOWNVOTE,
        )

        assert result is not None
        assert result.vote_type == db_models.VoteType.DOWNVOTE

    def test_vote_on_idea_nonexistent_idea(self, db_session, test_user):
        """Voting on nonexistent idea raises IdeaNotFoundException."""
        with pytest.raises(IdeaNotFoundException):
            VoteService.vote_on_idea(
                db=db_session,
                idea_id=99999,
                user_id=test_user.id,
                vote_type=db_models.VoteType.UPVOTE,
            )

    def test_vote_on_pending_idea_fails(self, db_session, other_user, pending_idea):
        """Cannot vote on pending idea."""
        with pytest.raises(BusinessRuleException):
            VoteService.vote_on_idea(
                db=db_session,
                idea_id=pending_idea.id,
                user_id=other_user.id,
                vote_type=db_models.VoteType.UPVOTE,
            )

    def test_vote_on_own_idea_fails(self, db_session, test_user, test_idea):
        """Cannot vote on your own idea."""
        with pytest.raises(BusinessRuleException) as exc_info:
            VoteService.vote_on_idea(
                db=db_session,
                idea_id=test_idea.id,
                user_id=test_user.id,
                vote_type=db_models.VoteType.UPVOTE,
            )
        assert "own idea" in str(exc_info.value).lower()

    def test_change_vote_type(self, db_session, other_user, test_idea):
        """Changing vote type updates existing vote."""
        # First upvote
        VoteService.vote_on_idea(
            db=db_session,
            idea_id=test_idea.id,
            user_id=other_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )

        # Change to downvote
        result = VoteService.vote_on_idea(
            db=db_session,
            idea_id=test_idea.id,
            user_id=other_user.id,
            vote_type=db_models.VoteType.DOWNVOTE,
        )

        assert result is not None
        assert result.vote_type == db_models.VoteType.DOWNVOTE

    def test_get_user_vote(self, db_session, other_user, test_idea):
        """Can retrieve user's vote on an idea."""
        VoteService.vote_on_idea(
            db=db_session,
            idea_id=test_idea.id,
            user_id=other_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )

        vote = VoteService.get_user_vote(
            db=db_session,
            idea_id=test_idea.id,
            user_id=other_user.id,
        )

        assert vote is not None
        assert vote.vote_type == db_models.VoteType.UPVOTE

    def test_get_user_vote_none(self, db_session, test_user, test_idea):
        """Returns None when user hasn't voted."""
        vote = VoteService.get_user_vote(
            db=db_session,
            idea_id=test_idea.id,
            user_id=test_user.id,
        )

        assert vote is None

    def test_remove_vote(self, db_session, other_user, test_idea):
        """Can remove a vote."""
        VoteService.vote_on_idea(
            db=db_session,
            idea_id=test_idea.id,
            user_id=other_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )

        VoteService.remove_vote(
            db=db_session,
            idea_id=test_idea.id,
            user_id=other_user.id,
        )

        vote = VoteService.get_user_vote(db_session, test_idea.id, other_user.id)
        assert vote is None

    def test_remove_vote_not_found(self, db_session, other_user, test_idea):
        """Raises VoteNotFoundException when trying to remove non-existent vote."""
        with pytest.raises(VoteNotFoundException):
            VoteService.remove_vote(
                db=db_session,
                idea_id=test_idea.id,
                user_id=other_user.id,
            )
