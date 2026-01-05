"""Tests for VoteQualityRepository."""

import pytest

import repositories.db_models as db_models
from repositories.vote_quality_repository import VoteQualityRepository


@pytest.fixture
def test_qualities(db_session) -> list[db_models.Quality]:
    """Create multiple test qualities."""
    qualities = []
    for i, key in enumerate(["quality_1", "quality_2", "quality_3"]):
        quality = db_models.Quality(
            key=key,
            name_en=f"Quality {i + 1}",
            name_fr=f"Qualité {i + 1}",
            is_default=True,
            is_active=True,
            display_order=i + 1,
        )
        db_session.add(quality)
        qualities.append(quality)
    db_session.commit()
    for q in qualities:
        db_session.refresh(q)
    return qualities


@pytest.fixture
def test_vote(db_session, test_user, test_idea) -> db_models.Vote:
    """Create a test upvote."""
    vote = db_models.Vote(
        idea_id=test_idea.id,
        user_id=test_user.id,
        vote_type=db_models.VoteType.UPVOTE,
    )
    db_session.add(vote)
    db_session.commit()
    db_session.refresh(vote)
    return vote


@pytest.fixture
def vote_with_qualities(
    db_session, test_vote, test_qualities
) -> tuple[db_models.Vote, list[db_models.VoteQuality]]:
    """Create a vote with attached qualities."""
    vote_qualities = []
    for quality in test_qualities[:2]:  # Attach first 2 qualities
        vq = db_models.VoteQuality(
            vote_id=test_vote.id,
            quality_id=quality.id,
        )
        db_session.add(vq)
        vote_qualities.append(vq)
    db_session.commit()
    for vq in vote_qualities:
        db_session.refresh(vq)
    return test_vote, vote_qualities


class TestVoteQualityRepository:
    """Test cases for VoteQualityRepository."""

    def test_get_by_vote_id(self, db_session, vote_with_qualities):
        """Get all vote qualities for a vote."""
        vote, expected_vqs = vote_with_qualities

        repo = VoteQualityRepository(db_session)
        results = repo.get_by_vote_id(vote.id)

        assert len(results) == 2
        assert all(vq.vote_id == vote.id for vq in results)

    def test_get_by_vote_id_empty(self, db_session, test_vote):
        """Get vote qualities returns empty list when none attached."""
        repo = VoteQualityRepository(db_session)
        results = repo.get_by_vote_id(test_vote.id)
        assert results == []

    def test_get_quality_ids_by_vote(self, db_session, vote_with_qualities):
        """Get list of quality IDs for a vote."""
        vote, vote_qualities = vote_with_qualities

        repo = VoteQualityRepository(db_session)
        results = repo.get_quality_ids_by_vote(vote.id)

        assert len(results) == 2
        assert all(isinstance(qid, int) for qid in results)
        expected_ids = [vq.quality_id for vq in vote_qualities]
        assert set(results) == set(expected_ids)

    def test_get_quality_ids_by_vote_empty(self, db_session, test_vote):
        """Get quality IDs returns empty list when none attached."""
        repo = VoteQualityRepository(db_session)
        results = repo.get_quality_ids_by_vote(test_vote.id)
        assert results == []

    def test_set_qualities(self, db_session, test_vote, test_qualities):
        """Set qualities for a vote."""
        repo = VoteQualityRepository(db_session)
        quality_ids = [test_qualities[0].id, test_qualities[1].id]

        results = repo.set_qualities(test_vote.id, quality_ids)

        assert len(results) == 2
        assert all(vq.vote_id == test_vote.id for vq in results)

        # Verify persisted
        fetched = repo.get_quality_ids_by_vote(test_vote.id)
        assert set(fetched) == set(quality_ids)

    def test_set_qualities_replaces_existing(
        self, db_session, vote_with_qualities, test_qualities
    ):
        """Set qualities replaces existing qualities."""
        vote, _ = vote_with_qualities

        repo = VoteQualityRepository(db_session)
        # Replace with only the third quality
        new_quality_ids = [test_qualities[2].id]
        repo.set_qualities(vote.id, new_quality_ids)

        fetched = repo.get_quality_ids_by_vote(vote.id)
        assert fetched == new_quality_ids

    def test_set_qualities_deduplicates(self, db_session, test_vote, test_qualities):
        """Set qualities removes duplicates."""
        repo = VoteQualityRepository(db_session)
        # Pass duplicate IDs
        quality_ids = [
            test_qualities[0].id,
            test_qualities[0].id,
            test_qualities[1].id,
        ]

        results = repo.set_qualities(test_vote.id, quality_ids)

        assert len(results) == 2  # Only 2 unique IDs

    def test_clear_qualities(self, db_session, vote_with_qualities):
        """Clear all qualities from a vote."""
        vote, _ = vote_with_qualities

        repo = VoteQualityRepository(db_session)
        repo.clear_qualities(vote.id)
        db_session.commit()

        results = repo.get_by_vote_id(vote.id)
        assert results == []

    def test_clear_qualities_no_op_when_empty(self, db_session, test_vote):
        """Clear qualities does nothing when vote has no qualities."""
        repo = VoteQualityRepository(db_session)
        # Should not raise
        repo.clear_qualities(test_vote.id)
        db_session.commit()

    def test_get_counts_for_idea(
        self, db_session, test_idea, test_user, test_qualities
    ):
        """Get aggregated quality counts for an idea."""
        # Create multiple votes with qualities
        users = []
        for i in range(3):
            user = db_models.User(
                email=f"voter{i}@example.com",
                username=f"voter{i}",
                display_name=f"Voter {i}",
                hashed_password="hashedpwd",
                is_active=True,
            )
            db_session.add(user)
            users.append(user)
        db_session.commit()

        # Vote 1: quality_1
        vote1 = db_models.Vote(
            idea_id=test_idea.id,
            user_id=users[0].id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote1)
        db_session.commit()
        db_session.add(
            db_models.VoteQuality(vote_id=vote1.id, quality_id=test_qualities[0].id)
        )

        # Vote 2: quality_1, quality_2
        vote2 = db_models.Vote(
            idea_id=test_idea.id,
            user_id=users[1].id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote2)
        db_session.commit()
        db_session.add(
            db_models.VoteQuality(vote_id=vote2.id, quality_id=test_qualities[0].id)
        )
        db_session.add(
            db_models.VoteQuality(vote_id=vote2.id, quality_id=test_qualities[1].id)
        )

        # Vote 3: downvote with quality (should be excluded)
        vote3 = db_models.Vote(
            idea_id=test_idea.id,
            user_id=users[2].id,
            vote_type=db_models.VoteType.DOWNVOTE,
        )
        db_session.add(vote3)
        db_session.commit()
        db_session.add(
            db_models.VoteQuality(vote_id=vote3.id, quality_id=test_qualities[2].id)
        )
        db_session.commit()

        repo = VoteQualityRepository(db_session)
        counts = repo.get_counts_for_idea(test_idea.id)

        # quality_1: 2 votes, quality_2: 1 vote
        assert counts[test_qualities[0].id] == 2
        assert counts[test_qualities[1].id] == 1
        # quality_3 from downvote should not be counted
        assert test_qualities[2].id not in counts

    def test_get_counts_for_idea_empty(self, db_session, test_idea):
        """Get counts returns empty dict when no votes have qualities."""
        repo = VoteQualityRepository(db_session)
        counts = repo.get_counts_for_idea(test_idea.id)
        assert counts == {}

    def test_get_detailed_counts_for_idea(
        self, db_session, test_idea, test_user, test_qualities
    ):
        """Get detailed quality counts with keys for an idea."""
        # Create a vote with qualities
        vote = db_models.Vote(
            idea_id=test_idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.commit()

        db_session.add(
            db_models.VoteQuality(vote_id=vote.id, quality_id=test_qualities[0].id)
        )
        db_session.add(
            db_models.VoteQuality(vote_id=vote.id, quality_id=test_qualities[1].id)
        )
        db_session.commit()

        repo = VoteQualityRepository(db_session)
        results = repo.get_detailed_counts_for_idea(test_idea.id)

        assert len(results) == 2
        assert all("quality_id" in r for r in results)
        assert all("quality_key" in r for r in results)
        assert all("count" in r for r in results)

        keys = [r["quality_key"] for r in results]
        assert "quality_1" in keys
        assert "quality_2" in keys

    def test_count_votes_with_qualities(
        self, db_session, test_idea, test_user, test_qualities
    ):
        """Count votes that have at least one quality attached."""
        # Create users for voting
        users = []
        for i in range(3):
            user = db_models.User(
                email=f"counter{i}@example.com",
                username=f"counter{i}",
                display_name=f"Counter {i}",
                hashed_password="hashedpwd",
                is_active=True,
            )
            db_session.add(user)
            users.append(user)
        db_session.commit()

        # Vote 1: has qualities
        vote1 = db_models.Vote(
            idea_id=test_idea.id,
            user_id=users[0].id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote1)
        db_session.commit()
        db_session.add(
            db_models.VoteQuality(vote_id=vote1.id, quality_id=test_qualities[0].id)
        )

        # Vote 2: has qualities (2 qualities)
        vote2 = db_models.Vote(
            idea_id=test_idea.id,
            user_id=users[1].id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote2)
        db_session.commit()
        db_session.add(
            db_models.VoteQuality(vote_id=vote2.id, quality_id=test_qualities[0].id)
        )
        db_session.add(
            db_models.VoteQuality(vote_id=vote2.id, quality_id=test_qualities[1].id)
        )

        # Vote 3: no qualities
        vote3 = db_models.Vote(
            idea_id=test_idea.id,
            user_id=users[2].id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote3)
        db_session.commit()

        repo = VoteQualityRepository(db_session)
        count = repo.count_votes_with_qualities(test_idea.id)

        # Only 2 votes have qualities (vote3 has none)
        assert count == 2

    def test_count_votes_with_qualities_excludes_downvotes(
        self, db_session, test_idea, test_user, test_qualities
    ):
        """Count votes with qualities excludes downvotes."""
        # Create upvote with quality
        upvote = db_models.Vote(
            idea_id=test_idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(upvote)
        db_session.commit()
        db_session.add(
            db_models.VoteQuality(vote_id=upvote.id, quality_id=test_qualities[0].id)
        )

        # Create another user for downvote
        other_user = db_models.User(
            email="downvoter@example.com",
            username="downvoter",
            display_name="Downvoter",
            hashed_password="hashedpwd",
            is_active=True,
        )
        db_session.add(other_user)
        db_session.commit()

        # Create downvote with quality
        downvote = db_models.Vote(
            idea_id=test_idea.id,
            user_id=other_user.id,
            vote_type=db_models.VoteType.DOWNVOTE,
        )
        db_session.add(downvote)
        db_session.commit()
        db_session.add(
            db_models.VoteQuality(vote_id=downvote.id, quality_id=test_qualities[1].id)
        )
        db_session.commit()

        repo = VoteQualityRepository(db_session)
        count = repo.count_votes_with_qualities(test_idea.id)

        # Only upvotes count
        assert count == 1

    def test_count_votes_with_qualities_zero(self, db_session, test_idea):
        """Count returns 0 when no votes have qualities."""
        repo = VoteQualityRepository(db_session)
        count = repo.count_votes_with_qualities(test_idea.id)
        assert count == 0

    def test_cascade_delete_on_vote(
        self, db_session, vote_with_qualities, test_qualities
    ):
        """Vote qualities are deleted when vote is deleted."""
        vote, vote_qualities = vote_with_qualities
        vote_id = vote.id

        # Delete the vote
        db_session.delete(vote)
        db_session.commit()

        # Vote qualities should be gone
        repo = VoteQualityRepository(db_session)
        results = repo.get_by_vote_id(vote_id)
        assert results == []

    def test_cascade_delete_on_quality(self, db_session, test_vote, test_qualities):
        """Vote qualities are deleted when quality is deleted."""
        # Add quality to vote
        vq = db_models.VoteQuality(
            vote_id=test_vote.id,
            quality_id=test_qualities[0].id,
        )
        db_session.add(vq)
        db_session.commit()

        # Delete the quality
        db_session.delete(test_qualities[0])
        db_session.commit()

        # Vote quality should be gone
        repo = VoteQualityRepository(db_session)
        results = repo.get_by_vote_id(test_vote.id)
        assert len(results) == 0
