"""Tests for ShareService."""

import pytest

import repositories.db_models as db_models
from models.exceptions import IdeaNotFoundException
from models.schemas import SharePlatform
from services.share_service import ShareService


class TestShareService:
    """Test suite for ShareService."""

    def test_record_share_success(self, db_session, test_idea):
        """Should record a share event successfully."""
        response = ShareService.record_share(
            db=db_session,
            idea_id=test_idea.id,
            platform=SharePlatform.TWITTER,
            referrer_url="https://example.com/share",
        )

        assert response.idea_id == test_idea.id
        assert response.platform == SharePlatform.TWITTER
        assert response.id is not None
        assert response.created_at is not None

    def test_record_share_without_referrer(self, db_session, test_idea):
        """Should record a share event without referrer URL."""
        response = ShareService.record_share(
            db=db_session,
            idea_id=test_idea.id,
            platform=SharePlatform.FACEBOOK,
        )

        assert response.idea_id == test_idea.id
        assert response.platform == SharePlatform.FACEBOOK

    def test_record_share_idea_not_found(self, db_session):
        """Should raise exception when idea not found."""
        with pytest.raises(IdeaNotFoundException):
            ShareService.record_share(
                db=db_session,
                idea_id=99999,
                platform=SharePlatform.TWITTER,
            )

    def test_record_share_all_platforms(self, db_session, test_idea):
        """Should record shares for all platforms."""
        platforms = [
            SharePlatform.TWITTER,
            SharePlatform.FACEBOOK,
            SharePlatform.LINKEDIN,
            SharePlatform.WHATSAPP,
            SharePlatform.COPY_LINK,
        ]

        for platform in platforms:
            response = ShareService.record_share(
                db=db_session,
                idea_id=test_idea.id,
                platform=platform,
            )
            assert response.platform == platform

    def test_get_idea_share_analytics_success(self, db_session, test_idea):
        """Should return share analytics for an idea."""
        # Create some shares first
        ShareService.record_share(db_session, test_idea.id, SharePlatform.TWITTER)
        ShareService.record_share(db_session, test_idea.id, SharePlatform.TWITTER)
        ShareService.record_share(db_session, test_idea.id, SharePlatform.FACEBOOK)

        analytics = ShareService.get_idea_share_analytics(db_session, test_idea.id)

        assert analytics.idea_id == test_idea.id
        assert analytics.total_shares == 3
        assert analytics.by_platform["twitter"] == 2
        assert analytics.by_platform["facebook"] == 1
        assert analytics.last_7_days == 3

    def test_get_idea_share_analytics_no_shares(self, db_session, test_idea):
        """Should return zero counts for idea with no shares."""
        analytics = ShareService.get_idea_share_analytics(db_session, test_idea.id)

        assert analytics.idea_id == test_idea.id
        assert analytics.total_shares == 0
        assert analytics.by_platform == {}
        assert analytics.last_7_days == 0

    def test_get_idea_share_analytics_not_found(self, db_session):
        """Should raise exception when idea not found."""
        with pytest.raises(IdeaNotFoundException):
            ShareService.get_idea_share_analytics(db_session, idea_id=99999)

    def test_get_top_shared_ideas(self, db_session, test_user, test_category):
        """Should return top shared ideas."""
        # Create two ideas
        idea1 = db_models.Idea(
            title="Popular Idea",
            description="A very popular idea description.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        idea2 = db_models.Idea(
            title="Less Popular Idea",
            description="A less popular idea description.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        db_session.add(idea1)
        db_session.add(idea2)
        db_session.commit()
        db_session.refresh(idea1)
        db_session.refresh(idea2)

        # Share idea1 more
        ShareService.record_share(db_session, idea1.id, SharePlatform.TWITTER)
        ShareService.record_share(db_session, idea1.id, SharePlatform.TWITTER)
        ShareService.record_share(db_session, idea2.id, SharePlatform.FACEBOOK)

        top_ideas = ShareService.get_top_shared_ideas(db_session, limit=5)

        assert len(top_ideas) == 2
        assert top_ideas[0].idea_id == idea1.id
        assert top_ideas[0].total_shares == 2
        assert top_ideas[1].idea_id == idea2.id
        assert top_ideas[1].total_shares == 1

    def test_get_top_shared_ideas_empty(self, db_session):
        """Should return empty list when no shares."""
        top_ideas = ShareService.get_top_shared_ideas(db_session)

        assert top_ideas == []

    def test_get_admin_share_analytics(self, db_session, test_idea):
        """Should return admin analytics overview."""
        # Create shares
        ShareService.record_share(db_session, test_idea.id, SharePlatform.TWITTER)
        ShareService.record_share(db_session, test_idea.id, SharePlatform.FACEBOOK)
        ShareService.record_share(db_session, test_idea.id, SharePlatform.TWITTER)

        analytics = ShareService.get_admin_share_analytics(db_session)

        assert analytics.total_shares == 3
        assert analytics.platform_distribution["twitter"] == 2
        assert analytics.platform_distribution["facebook"] == 1
        assert analytics.shares_last_7_days == 3
        assert analytics.shares_last_30_days == 3
        assert len(analytics.top_shared_ideas) == 1
        assert analytics.generated_at is not None

    def test_get_admin_share_analytics_empty(self, db_session):
        """Should return zero analytics when no shares."""
        analytics = ShareService.get_admin_share_analytics(db_session)

        assert analytics.total_shares == 0
        assert analytics.platform_distribution == {}
        assert analytics.top_shared_ideas == []
        assert analytics.shares_last_7_days == 0
        assert analytics.shares_last_30_days == 0
