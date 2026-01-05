"""Tests for VoteRepository."""

import repositories.db_models as db_models
from repositories.vote_repository import VoteRepository


class TestVoteRepository:
    """Test cases for VoteRepository."""

    def test_get_by_idea_and_user_found(self, db_session, test_user, test_idea):
        """Get vote by idea and user when vote exists."""
        # Create a vote
        vote = db_models.Vote(
            idea_id=test_idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.commit()

        # Test repository method
        repo = VoteRepository(db_session)
        result = repo.get_by_idea_and_user(test_idea.id, test_user.id)

        assert result is not None
        assert result.idea_id == test_idea.id
        assert result.user_id == test_user.id
        assert result.vote_type == db_models.VoteType.UPVOTE

    def test_get_by_idea_and_user_not_found(self, db_session, test_user, test_idea):
        """Get vote returns None when vote doesn't exist."""
        repo = VoteRepository(db_session)
        result = repo.get_by_idea_and_user(test_idea.id, test_user.id)
        assert result is None

    def test_get_votes_for_idea_all(self, db_session, test_idea, create_votes):
        """Get all votes for an idea."""
        # Create votes
        create_votes(test_idea.id, upvotes=3, downvotes=2)

        repo = VoteRepository(db_session)
        votes = repo.get_votes_for_idea(test_idea.id)

        assert len(votes) == 5

    def test_get_votes_for_idea_filtered_upvotes(
        self, db_session, test_idea, create_votes
    ):
        """Get only upvotes for an idea."""
        create_votes(test_idea.id, upvotes=3, downvotes=2)

        repo = VoteRepository(db_session)
        votes = repo.get_votes_for_idea(test_idea.id, db_models.VoteType.UPVOTE)

        assert len(votes) == 3
        assert all(v.vote_type == db_models.VoteType.UPVOTE for v in votes)

    def test_get_votes_for_idea_filtered_downvotes(
        self, db_session, test_idea, create_votes
    ):
        """Get only downvotes for an idea."""
        create_votes(test_idea.id, upvotes=3, downvotes=2)

        repo = VoteRepository(db_session)
        votes = repo.get_votes_for_idea(test_idea.id, db_models.VoteType.DOWNVOTE)

        assert len(votes) == 2
        assert all(v.vote_type == db_models.VoteType.DOWNVOTE for v in votes)

    def test_get_votes_by_user(self, db_session, test_user, test_idea, pending_idea):
        """Get all votes by a user."""
        # User votes on two ideas
        vote1 = db_models.Vote(
            idea_id=test_idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        vote2 = db_models.Vote(
            idea_id=pending_idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.DOWNVOTE,
        )
        db_session.add(vote1)
        db_session.add(vote2)
        db_session.commit()

        repo = VoteRepository(db_session)
        votes = repo.get_votes_by_user(test_user.id)

        assert len(votes) == 2
        assert all(v.user_id == test_user.id for v in votes)

    def test_get_votes_by_user_pagination(self, db_session, test_user, test_category):
        """Get votes by user with pagination."""
        # Create multiple ideas and votes
        for i in range(5):
            idea = db_models.Idea(
                title=f"Idea {i}",
                description=f"Description for idea {i} that is long enough.",
                category_id=test_category.id,
                user_id=test_user.id,
                status=db_models.IdeaStatus.APPROVED,
            )
            db_session.add(idea)
            db_session.commit()
            db_session.refresh(idea)

            vote = db_models.Vote(
                idea_id=idea.id,
                user_id=test_user.id,
                vote_type=db_models.VoteType.UPVOTE,
            )
            db_session.add(vote)
        db_session.commit()

        repo = VoteRepository(db_session)

        # Test pagination
        page1 = repo.get_votes_by_user(test_user.id, skip=0, limit=2)
        page2 = repo.get_votes_by_user(test_user.id, skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    def test_delete_by_idea_and_user_success(self, db_session, test_user, test_idea):
        """Delete vote successfully."""
        # Create a vote
        vote = db_models.Vote(
            idea_id=test_idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.commit()

        repo = VoteRepository(db_session)
        result = repo.delete_by_idea_and_user(test_idea.id, test_user.id)

        assert result is True
        # Verify vote is deleted
        remaining = repo.get_by_idea_and_user(test_idea.id, test_user.id)
        assert remaining is None

    def test_delete_by_idea_and_user_not_found(self, db_session, test_user, test_idea):
        """Delete returns False when vote doesn't exist."""
        repo = VoteRepository(db_session)
        result = repo.delete_by_idea_and_user(test_idea.id, test_user.id)
        assert result is False
