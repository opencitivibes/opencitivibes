"""
Tests for AnalyticsService.
"""

from datetime import datetime, timedelta, timezone

import pytest

import repositories.db_models as db_models
from models.exceptions import ValidationException
from models.schemas import ContributorType, Granularity
from services.analytics_service import AnalyticsService


class TestAnalyticsServiceOverview:
    """Tests for get_overview method."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        AnalyticsService.invalidate_cache()

    def test_get_overview_returns_metrics(self, db_session) -> None:
        """Test that get_overview returns all expected metrics."""
        result = AnalyticsService.get_overview(db_session)

        assert hasattr(result, "total_users")
        assert hasattr(result, "total_ideas")
        assert hasattr(result, "ideas_this_week")
        assert hasattr(result, "generated_at")

    def test_get_overview_empty_database(self, db_session) -> None:
        """Test overview with empty database returns zeros."""
        result = AnalyticsService.get_overview(db_session)

        assert result.total_users == 0
        assert result.total_ideas == 0
        assert result.total_votes == 0
        assert result.total_comments == 0

    def test_get_overview_with_data(
        self, db_session, test_user, test_category, test_idea
    ) -> None:
        """Test overview with actual data."""
        result = AnalyticsService.get_overview(db_session)

        assert result.total_users >= 1
        assert result.total_ideas >= 1
        assert result.approved_ideas >= 1

    def test_get_overview_caches_result(self, db_session) -> None:
        """Test that subsequent calls use cached data."""
        result1 = AnalyticsService.get_overview(db_session)
        result2 = AnalyticsService.get_overview(db_session)

        # Same generated_at means cached
        assert result1.generated_at == result2.generated_at

    def test_cache_invalidation(self, db_session) -> None:
        """Test that cache can be invalidated."""
        AnalyticsService.get_overview(db_session)
        assert "overview" in AnalyticsService._cache

        AnalyticsService.invalidate_cache("overview")
        assert "overview" not in AnalyticsService._cache

    def test_cache_invalidation_all(self, db_session) -> None:
        """Test that all cache can be cleared."""
        AnalyticsService.get_overview(db_session)
        AnalyticsService.get_categories_analytics(db_session)

        AnalyticsService.invalidate_cache()
        assert len(AnalyticsService._cache) == 0


class TestAnalyticsServiceTrends:
    """Tests for get_trends method."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        AnalyticsService.invalidate_cache()

    def test_get_trends_validates_date_range(self, db_session) -> None:
        """Test that invalid date range raises exception."""
        with pytest.raises(ValidationException):
            AnalyticsService.get_trends(
                db_session,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) - timedelta(days=1),
                granularity=Granularity.DAY,
            )

    def test_get_trends_rejects_large_range(self, db_session) -> None:
        """Test that date range over 2 years is rejected."""
        with pytest.raises(ValidationException):
            AnalyticsService.get_trends(
                db_session,
                start_date=datetime(2020, 1, 1),
                end_date=datetime(2025, 1, 1),
                granularity=Granularity.MONTH,
            )

    def test_get_trends_daily(self, db_session) -> None:
        """Test daily trends aggregation."""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)

        result = AnalyticsService.get_trends(
            db_session, start_date=start, end_date=end, granularity=Granularity.DAY
        )

        assert result.granularity == Granularity.DAY
        assert result.start_date == start
        assert result.end_date == end
        assert isinstance(result.data, list)

    def test_get_trends_weekly(self, db_session) -> None:
        """Test weekly trends aggregation."""
        start = datetime.now(timezone.utc) - timedelta(days=30)
        end = datetime.now(timezone.utc)

        result = AnalyticsService.get_trends(
            db_session, start_date=start, end_date=end, granularity=Granularity.WEEK
        )

        assert result.granularity == Granularity.WEEK

    def test_get_trends_monthly(self, db_session) -> None:
        """Test monthly trends aggregation."""
        start = datetime.now(timezone.utc) - timedelta(days=180)
        end = datetime.now(timezone.utc)

        result = AnalyticsService.get_trends(
            db_session, start_date=start, end_date=end, granularity=Granularity.MONTH
        )

        assert result.granularity == Granularity.MONTH

    def test_get_trends_caches_result(self, db_session) -> None:
        """Test that trends are cached."""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)

        result1 = AnalyticsService.get_trends(
            db_session, start_date=start, end_date=end, granularity=Granularity.DAY
        )
        result2 = AnalyticsService.get_trends(
            db_session, start_date=start, end_date=end, granularity=Granularity.DAY
        )

        # Cached result has same data
        assert len(result1.data) == len(result2.data)


class TestAnalyticsServiceCategories:
    """Tests for get_categories_analytics method."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        AnalyticsService.invalidate_cache()

    def test_get_categories_analytics_empty(self, db_session) -> None:
        """Test categories analytics with no categories."""
        result = AnalyticsService.get_categories_analytics(db_session)

        assert result.categories == []
        assert result.generated_at is not None

    def test_get_categories_analytics_with_data(
        self, db_session, test_category, test_idea
    ) -> None:
        """Test categories analytics with data."""
        result = AnalyticsService.get_categories_analytics(db_session)

        assert len(result.categories) >= 1
        category = result.categories[0]
        assert category.id == test_category.id
        assert category.total_ideas >= 1

    def test_get_categories_analytics_caches_result(
        self, db_session, test_category
    ) -> None:
        """Test that categories analytics are cached."""
        result1 = AnalyticsService.get_categories_analytics(db_session)
        result2 = AnalyticsService.get_categories_analytics(db_session)

        assert result1.generated_at == result2.generated_at


class TestAnalyticsServiceContributors:
    """Tests for get_top_contributors method."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        AnalyticsService.invalidate_cache()

    def test_get_top_contributors_validates_limit(self, db_session) -> None:
        """Test that limit outside 5-50 range raises exception."""
        with pytest.raises(ValidationException):
            AnalyticsService.get_top_contributors(
                db_session, contributor_type=ContributorType.IDEAS, limit=100
            )

    def test_get_top_contributors_validates_limit_too_small(self, db_session) -> None:
        """Test that limit below 5 raises exception."""
        with pytest.raises(ValidationException):
            AnalyticsService.get_top_contributors(
                db_session, contributor_type=ContributorType.IDEAS, limit=2
            )

    def test_get_top_contributors_by_ideas_empty(self, db_session) -> None:
        """Test top contributors with no data."""
        result = AnalyticsService.get_top_contributors(
            db_session, contributor_type=ContributorType.IDEAS, limit=10
        )

        assert result.type == ContributorType.IDEAS
        assert result.contributors == []

    def test_get_top_contributors_by_ideas(
        self, db_session, test_user, test_idea
    ) -> None:
        """Test top contributors by ideas with data."""
        result = AnalyticsService.get_top_contributors(
            db_session, contributor_type=ContributorType.IDEAS, limit=10
        )

        assert result.type == ContributorType.IDEAS
        assert len(result.contributors) >= 1
        assert result.contributors[0].rank == 1

    def test_get_top_contributors_by_votes(
        self, db_session, test_user, test_idea, create_votes
    ) -> None:
        """Test top contributors by votes."""
        create_votes(test_idea.id, upvotes=3, downvotes=1)

        result = AnalyticsService.get_top_contributors(
            db_session, contributor_type=ContributorType.VOTES, limit=10
        )

        assert result.type == ContributorType.VOTES

    def test_get_top_contributors_by_comments(
        self, db_session, test_user, test_idea
    ) -> None:
        """Test top contributors by comments."""
        # Add a comment
        comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment for analytics",
        )
        db_session.add(comment)
        db_session.commit()

        result = AnalyticsService.get_top_contributors(
            db_session, contributor_type=ContributorType.COMMENTS, limit=10
        )

        assert result.type == ContributorType.COMMENTS
        assert len(result.contributors) >= 1

    def test_get_top_contributors_caches_result(
        self, db_session, test_user, test_idea
    ) -> None:
        """Test that contributors are cached."""
        result1 = AnalyticsService.get_top_contributors(
            db_session, contributor_type=ContributorType.IDEAS, limit=10
        )
        result2 = AnalyticsService.get_top_contributors(
            db_session, contributor_type=ContributorType.IDEAS, limit=10
        )

        assert result1.generated_at == result2.generated_at


class TestOfficialsAnalyticsMethods:
    """Tests for officials analytics methods."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        AnalyticsService.invalidate_cache()

    def test_get_quality_overview_for_officials_empty(self, db_session) -> None:
        """Test quality overview with no data."""
        result = AnalyticsService.get_quality_overview_for_officials(db_session)

        assert result["total_upvotes"] == 0
        assert result["votes_with_qualities"] == 0
        assert result["adoption_rate"] == 0.0
        assert "quality_distribution" in result

    def test_get_quality_overview_for_officials_with_data(
        self, db_session, test_user, test_idea
    ) -> None:
        """Test quality overview with upvotes."""
        # Create an upvote
        vote = db_models.Vote(
            idea_id=test_idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.commit()

        result = AnalyticsService.get_quality_overview_for_officials(db_session)

        assert result["total_upvotes"] >= 1
        assert "quality_distribution" in result

    def test_get_top_ideas_by_quality_for_officials_empty(self, db_session) -> None:
        """Test top ideas by quality with no data."""
        result = AnalyticsService.get_top_ideas_by_quality_for_officials(db_session)

        assert result == []

    def test_get_top_ideas_by_quality_for_officials_limit(
        self, db_session, test_user, test_idea, test_quality
    ) -> None:
        """Test top ideas by quality with limit."""
        # Create upvote with quality
        vote = db_models.Vote(
            idea_id=test_idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.flush()

        vote_quality = db_models.VoteQuality(
            vote_id=vote.id,
            quality_id=test_quality.id,
        )
        db_session.add(vote_quality)
        db_session.commit()

        result = AnalyticsService.get_top_ideas_by_quality_for_officials(
            db_session, limit=5
        )

        assert len(result) <= 5
        if result:
            assert "idea_id" in result[0]
            assert "title" in result[0]
            assert "quality_count" in result[0]

    def test_get_top_ideas_by_quality_for_officials_filter(
        self, db_session, test_user, test_idea, test_quality
    ) -> None:
        """Test top ideas filtered by quality key."""
        # Create upvote with quality
        vote = db_models.Vote(
            idea_id=test_idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.flush()

        vote_quality = db_models.VoteQuality(
            vote_id=vote.id,
            quality_id=test_quality.id,
        )
        db_session.add(vote_quality)
        db_session.commit()

        result = AnalyticsService.get_top_ideas_by_quality_for_officials(
            db_session, quality_key=test_quality.key, limit=10
        )

        # All results should have this quality
        for r in result:
            assert r["quality_count"] >= 1

    def test_get_ideas_with_quality_stats_for_officials_empty(self, db_session) -> None:
        """Test ideas with quality stats with no data."""
        result = AnalyticsService.get_ideas_with_quality_stats_for_officials(db_session)

        assert result["total"] == 0
        assert result["items"] == []

    def test_get_ideas_with_quality_stats_for_officials_pagination(
        self, db_session, test_user, test_category
    ) -> None:
        """Test pagination for ideas with quality stats."""
        # Create multiple approved ideas
        for i in range(5):
            idea = db_models.Idea(
                title=f"Test Idea {i}",
                description=f"Description {i}",
                user_id=test_user.id,
                category_id=test_category.id,
                status=db_models.IdeaStatus.APPROVED,
            )
            db_session.add(idea)
        db_session.commit()

        result = AnalyticsService.get_ideas_with_quality_stats_for_officials(
            db_session, skip=0, limit=2
        )

        assert result["total"] >= 5
        assert len(result["items"]) == 2

    def test_get_ideas_with_quality_stats_for_officials_category_filter(
        self, db_session, test_user, test_category, test_idea
    ) -> None:
        """Test category filter for ideas with quality stats."""
        result = AnalyticsService.get_ideas_with_quality_stats_for_officials(
            db_session, category_id=test_category.id
        )

        for item in result["items"]:
            assert item["idea"].category_id == test_category.id

    def test_get_ideas_with_quality_stats_for_officials_sorting(
        self, db_session, test_user, test_category
    ) -> None:
        """Test sorting options for ideas with quality stats."""
        import time

        # Create ideas with different created_at times
        for i in range(3):
            idea = db_models.Idea(
                title=f"Test Idea {i}",
                description=f"Description {i}",
                user_id=test_user.id,
                category_id=test_category.id,
                status=db_models.IdeaStatus.APPROVED,
            )
            db_session.add(idea)
            db_session.flush()
            time.sleep(0.01)  # Ensure different created_at times
        db_session.commit()

        result = AnalyticsService.get_ideas_with_quality_stats_for_officials(
            db_session, sort_by="created_at", sort_order="desc"
        )

        if len(result["items"]) >= 2:
            assert (
                result["items"][0]["idea"].created_at
                >= result["items"][1]["idea"].created_at
            )

    def test_get_category_quality_breakdown_for_officials_empty(
        self, db_session
    ) -> None:
        """Test category quality breakdown with no data."""
        result = AnalyticsService.get_category_quality_breakdown_for_officials(
            db_session
        )

        assert result == []

    def test_get_category_quality_breakdown_for_officials_with_data(
        self, db_session, test_user, test_idea
    ) -> None:
        """Test category quality breakdown with data."""
        # Create an upvote
        vote = db_models.Vote(
            idea_id=test_idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.commit()

        result = AnalyticsService.get_category_quality_breakdown_for_officials(
            db_session
        )

        assert len(result) >= 1
        assert "category_id" in result[0]
        assert "idea_count" in result[0]
        assert "quality_count" in result[0]

    def test_get_time_series_data_for_officials_empty(self, db_session) -> None:
        """Test time series data with no data."""
        result = AnalyticsService.get_time_series_data_for_officials(db_session)

        assert result == []

    def test_get_time_series_data_for_officials_with_data(
        self, db_session, test_user, test_idea, test_quality
    ) -> None:
        """Test time series data with quality votes."""
        # Create upvote with quality
        vote = db_models.Vote(
            idea_id=test_idea.id,
            user_id=test_user.id,
            vote_type=db_models.VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.flush()

        vote_quality = db_models.VoteQuality(
            vote_id=vote.id,
            quality_id=test_quality.id,
        )
        db_session.add(vote_quality)
        db_session.commit()

        result = AnalyticsService.get_time_series_data_for_officials(db_session, days=7)

        assert len(result) >= 1
        assert "date" in result[0]
        assert "count" in result[0]

    def test_get_time_series_data_for_officials_days_limit(self, db_session) -> None:
        """Test time series data respects days limit."""
        result = AnalyticsService.get_time_series_data_for_officials(
            db_session, days=30
        )

        # Result should be list of date/count pairs
        for item in result:
            assert "date" in item
            assert "count" in item
