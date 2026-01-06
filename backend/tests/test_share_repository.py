"""Tests for ShareRepository."""

import repositories.db_models as db_models
from repositories.share_repository import ShareRepository


class TestShareRepository:
    """Test suite for ShareRepository."""

    def test_create_share_event(self, db_session, test_idea):
        """Should create a share event."""
        repo = ShareRepository(db_session)
        share = repo.create_share_event(
            idea_id=test_idea.id,
            platform=db_models.SharePlatform.TWITTER,
            referrer_url="https://example.com/ideas/1",
        )

        assert share is not None
        assert share.idea_id == test_idea.id
        assert share.platform == db_models.SharePlatform.TWITTER
        assert share.referrer_url == "https://example.com/ideas/1"
        assert share.created_at is not None

    def test_create_share_event_without_referrer(self, db_session, test_idea):
        """Should create a share event without referrer URL."""
        repo = ShareRepository(db_session)
        share = repo.create_share_event(
            idea_id=test_idea.id,
            platform=db_models.SharePlatform.FACEBOOK,
        )

        assert share is not None
        assert share.referrer_url is None

    def test_get_share_counts_by_idea(self, db_session, test_idea):
        """Should return share counts by platform."""
        repo = ShareRepository(db_session)

        # Create multiple shares
        repo.create_share_event(test_idea.id, db_models.SharePlatform.TWITTER)
        repo.create_share_event(test_idea.id, db_models.SharePlatform.TWITTER)
        repo.create_share_event(test_idea.id, db_models.SharePlatform.FACEBOOK)

        counts = repo.get_share_counts_by_idea(test_idea.id)

        assert counts["total_shares"] == 3
        assert counts["by_platform"]["twitter"] == 2
        assert counts["by_platform"]["facebook"] == 1

    def test_get_share_counts_by_idea_no_shares(self, db_session, test_idea):
        """Should return zero counts for idea with no shares."""
        repo = ShareRepository(db_session)

        counts = repo.get_share_counts_by_idea(test_idea.id)

        assert counts["total_shares"] == 0
        assert counts["by_platform"] == {}

    def test_get_recent_share_count(self, db_session, test_idea):
        """Should return recent share count."""
        repo = ShareRepository(db_session)

        # Create shares
        repo.create_share_event(test_idea.id, db_models.SharePlatform.TWITTER)
        repo.create_share_event(test_idea.id, db_models.SharePlatform.FACEBOOK)
        db_session.commit()

        count = repo.get_recent_share_count(test_idea.id, days=7)

        assert count == 2

    def test_get_share_counts_by_idea_batch(self, db_session, test_user, test_category):
        """Should return batch share counts for multiple ideas."""
        repo = ShareRepository(db_session)

        # Create two ideas
        idea1 = db_models.Idea(
            title="Idea 1",
            description="First test idea description.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        idea2 = db_models.Idea(
            title="Idea 2",
            description="Second test idea description.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        db_session.add(idea1)
        db_session.add(idea2)
        db_session.commit()
        db_session.refresh(idea1)
        db_session.refresh(idea2)

        # Create shares for idea1
        repo.create_share_event(idea1.id, db_models.SharePlatform.TWITTER)
        repo.create_share_event(idea1.id, db_models.SharePlatform.TWITTER)
        # No shares for idea2

        counts = repo.get_share_counts_by_idea_batch([idea1.id, idea2.id])

        assert counts[idea1.id]["total_shares"] == 2
        assert counts[idea1.id]["by_platform"]["twitter"] == 2
        assert counts[idea2.id]["total_shares"] == 0
        assert counts[idea2.id]["by_platform"] == {}

    def test_get_share_counts_by_idea_batch_empty_list(self, db_session):
        """Should return empty dict for empty list."""
        repo = ShareRepository(db_session)

        counts = repo.get_share_counts_by_idea_batch([])

        assert counts == {}

    def test_get_total_shares(self, db_session, test_idea):
        """Should return total share count."""
        repo = ShareRepository(db_session)

        repo.create_share_event(test_idea.id, db_models.SharePlatform.TWITTER)
        repo.create_share_event(test_idea.id, db_models.SharePlatform.FACEBOOK)

        total = repo.get_total_shares()

        assert total == 2

    def test_get_total_shares_with_days_filter(self, db_session, test_idea):
        """Should respect days filter."""
        repo = ShareRepository(db_session)

        # Create share
        repo.create_share_event(test_idea.id, db_models.SharePlatform.TWITTER)
        db_session.commit()

        total_7_days = repo.get_total_shares(days=7)

        assert total_7_days == 1

    def test_get_platform_distribution(self, db_session, test_idea):
        """Should return platform distribution."""
        repo = ShareRepository(db_session)

        repo.create_share_event(test_idea.id, db_models.SharePlatform.TWITTER)
        repo.create_share_event(test_idea.id, db_models.SharePlatform.TWITTER)
        repo.create_share_event(test_idea.id, db_models.SharePlatform.FACEBOOK)
        repo.create_share_event(test_idea.id, db_models.SharePlatform.LINKEDIN)

        distribution = repo.get_platform_distribution()

        assert distribution["twitter"] == 2
        assert distribution["facebook"] == 1
        assert distribution["linkedin"] == 1

    def test_get_top_shared_ideas(self, db_session, test_user, test_category):
        """Should return top shared ideas."""
        repo = ShareRepository(db_session)

        # Create two ideas
        idea1 = db_models.Idea(
            title="Popular Idea",
            description="Very popular idea description.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        idea2 = db_models.Idea(
            title="Less Popular Idea",
            description="Less popular idea description.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        db_session.add(idea1)
        db_session.add(idea2)
        db_session.commit()
        db_session.refresh(idea1)
        db_session.refresh(idea2)

        # Idea1 gets more shares
        repo.create_share_event(idea1.id, db_models.SharePlatform.TWITTER)
        repo.create_share_event(idea1.id, db_models.SharePlatform.TWITTER)
        repo.create_share_event(idea1.id, db_models.SharePlatform.FACEBOOK)
        # Idea2 gets fewer shares
        repo.create_share_event(idea2.id, db_models.SharePlatform.LINKEDIN)

        top_ideas = repo.get_top_shared_ideas(limit=2)

        assert len(top_ideas) == 2
        assert top_ideas[0]["idea_id"] == idea1.id
        assert top_ideas[0]["title"] == "Popular Idea"
        assert top_ideas[0]["total_shares"] == 3
        assert top_ideas[1]["idea_id"] == idea2.id
        assert top_ideas[1]["total_shares"] == 1

    def test_get_top_shared_ideas_empty(self, db_session):
        """Should return empty list when no shares."""
        repo = ShareRepository(db_session)

        top_ideas = repo.get_top_shared_ideas()

        assert top_ideas == []

    def test_share_event_all_platforms(self, db_session, test_idea):
        """Should support all platforms."""
        repo = ShareRepository(db_session)

        platforms = [
            db_models.SharePlatform.TWITTER,
            db_models.SharePlatform.FACEBOOK,
            db_models.SharePlatform.LINKEDIN,
            db_models.SharePlatform.WHATSAPP,
            db_models.SharePlatform.COPY_LINK,
        ]

        for platform in platforms:
            share = repo.create_share_event(test_idea.id, platform)
            assert share.platform == platform

        counts = repo.get_share_counts_by_idea(test_idea.id)
        assert counts["total_shares"] == 5
        assert len(counts["by_platform"]) == 5
