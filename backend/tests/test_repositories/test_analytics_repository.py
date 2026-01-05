"""
Tests for AnalyticsRepository.
"""

from datetime import datetime, timedelta, timezone

import repositories.db_models as db_models
from repositories.analytics_repository import AnalyticsRepository


class TestAnalyticsRepositoryOverview:
    """Tests for overview count methods."""

    def test_get_overview_counts_empty(self, db_session) -> None:
        """Test overview counts with empty database."""
        result = AnalyticsRepository.get_overview_counts(db_session)

        assert result["total_users"] == 0
        assert result["active_users"] == 0
        assert result["total_ideas"] == 0
        assert result["approved_ideas"] == 0
        assert result["pending_ideas"] == 0
        assert result["rejected_ideas"] == 0
        assert result["total_votes"] == 0
        assert result["total_comments"] == 0

    def test_get_overview_counts_with_data(
        self, db_session, test_user, test_category, test_idea, pending_idea
    ) -> None:
        """Test overview counts with actual data."""
        result = AnalyticsRepository.get_overview_counts(db_session)

        assert result["total_users"] >= 1
        assert result["active_users"] >= 1
        assert result["total_ideas"] >= 2
        assert result["approved_ideas"] >= 1
        assert result["pending_ideas"] >= 1

    def test_get_overview_counts_excludes_deleted(
        self, db_session, test_user, test_category, test_idea, deleted_idea
    ) -> None:
        """Test that deleted ideas are excluded from counts."""
        result = AnalyticsRepository.get_overview_counts(db_session)

        # Should only count non-deleted ideas
        assert result["total_ideas"] == 1
        assert result["approved_ideas"] == 1

    def test_get_this_week_counts_empty(self, db_session) -> None:
        """Test weekly counts with empty database."""
        result = AnalyticsRepository.get_this_week_counts(db_session)

        assert result["ideas_this_week"] == 0
        assert result["votes_this_week"] == 0
        assert result["comments_this_week"] == 0
        assert result["users_this_week"] == 0

    def test_get_this_week_counts_with_data(
        self, db_session, test_user, test_category, test_idea
    ) -> None:
        """Test weekly counts with recent data."""
        result = AnalyticsRepository.get_this_week_counts(db_session)

        # Recently created entities should be counted
        assert result["ideas_this_week"] >= 1
        assert result["users_this_week"] >= 1


class TestAnalyticsRepositoryTrends:
    """Tests for trend data methods."""

    def test_get_daily_trends_empty(self, db_session) -> None:
        """Test daily trends with no data in range."""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)

        result = AnalyticsRepository.get_daily_trends(db_session, start, end)

        # Should return entries for each day in range
        assert len(result) == 8  # 7 days + today

    def test_get_daily_trends_structure(self, db_session) -> None:
        """Test daily trends returns correct structure."""
        start = datetime.now(timezone.utc) - timedelta(days=3)
        end = datetime.now(timezone.utc)

        result = AnalyticsRepository.get_daily_trends(db_session, start, end)

        assert len(result) >= 1
        first_entry = result[0]
        assert "period" in first_entry
        assert "ideas" in first_entry
        assert "votes" in first_entry
        assert "comments" in first_entry
        assert "users" in first_entry

    def test_get_weekly_trends_empty(self, db_session) -> None:
        """Test weekly trends with no data."""
        start = datetime.now(timezone.utc) - timedelta(days=30)
        end = datetime.now(timezone.utc)

        result = AnalyticsRepository.get_weekly_trends(db_session, start, end)

        # Returns empty list when no data
        assert isinstance(result, list)

    def test_get_monthly_trends_empty(self, db_session) -> None:
        """Test monthly trends with no data."""
        start = datetime.now(timezone.utc) - timedelta(days=90)
        end = datetime.now(timezone.utc)

        result = AnalyticsRepository.get_monthly_trends(db_session, start, end)

        assert isinstance(result, list)

    def test_get_daily_trends_with_data(
        self, db_session, test_user, test_category, test_idea
    ) -> None:
        """Test daily trends includes recent data."""
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)

        result = AnalyticsRepository.get_daily_trends(db_session, start, end)

        # Should have entries
        assert len(result) >= 1

        # At least one entry should have idea count > 0
        has_ideas = any(entry["ideas"] > 0 for entry in result)
        assert has_ideas


class TestAnalyticsRepositoryCategories:
    """Tests for category analytics methods."""

    def test_get_category_analytics_empty(self, db_session) -> None:
        """Test category analytics with no categories."""
        result = AnalyticsRepository.get_category_analytics(db_session)

        assert result == []

    def test_get_category_analytics_with_data(
        self, db_session, test_category, test_idea
    ) -> None:
        """Test category analytics with data."""
        result = AnalyticsRepository.get_category_analytics(db_session)

        assert len(result) >= 1
        category = result[0]
        assert category["id"] == test_category.id
        assert category["name_en"] == test_category.name_en
        assert category["name_fr"] == test_category.name_fr
        assert category["total_ideas"] >= 1
        assert category["approved_ideas"] >= 1
        assert "approval_rate" in category
        assert "avg_score" in category

    def test_get_category_analytics_approval_rate(
        self, db_session, test_category, test_idea, pending_idea
    ) -> None:
        """Test approval rate calculation."""
        result = AnalyticsRepository.get_category_analytics(db_session)

        category = result[0]
        # 1 approved, 1 pending = 50% approval rate
        assert category["approval_rate"] == 0.5


class TestAnalyticsRepositoryContributors:
    """Tests for top contributors methods."""

    def test_get_top_contributors_by_ideas_empty(self, db_session) -> None:
        """Test top contributors with no ideas."""
        result = AnalyticsRepository.get_top_contributors_by_ideas(db_session, limit=10)

        assert result == []

    def test_get_top_contributors_by_ideas_with_data(
        self, db_session, test_user, test_idea
    ) -> None:
        """Test top contributors by ideas."""
        result = AnalyticsRepository.get_top_contributors_by_ideas(db_session, limit=10)

        assert len(result) >= 1
        top_user = result[0]
        assert top_user["user_id"] == test_user.id
        assert top_user["rank"] == 1
        assert top_user["count"] >= 1

    def test_get_top_contributors_by_votes_empty(self, db_session) -> None:
        """Test top contributors with no votes."""
        result = AnalyticsRepository.get_top_contributors_by_votes(db_session, limit=10)

        assert result == []

    def test_get_top_contributors_by_votes_with_data(
        self, db_session, test_user, test_idea, create_votes
    ) -> None:
        """Test top contributors by votes."""
        create_votes(test_idea.id, upvotes=5, downvotes=2)

        result = AnalyticsRepository.get_top_contributors_by_votes(db_session, limit=10)

        assert len(result) >= 1
        # Each voter should appear once
        assert result[0]["count"] == 1  # Each created user voted once

    def test_get_top_contributors_by_comments_empty(self, db_session) -> None:
        """Test top contributors with no comments."""
        result = AnalyticsRepository.get_top_contributors_by_comments(
            db_session, limit=10
        )

        assert result == []

    def test_get_top_contributors_by_comments_with_data(
        self, db_session, test_user, test_idea
    ) -> None:
        """Test top contributors by comments."""
        # Add comments
        for i in range(3):
            comment = db_models.Comment(
                idea_id=test_idea.id,
                user_id=test_user.id,
                content=f"Test comment {i}",
            )
            db_session.add(comment)
        db_session.commit()

        result = AnalyticsRepository.get_top_contributors_by_comments(
            db_session, limit=10
        )

        assert len(result) >= 1
        assert result[0]["user_id"] == test_user.id
        assert result[0]["count"] == 3

    def test_get_top_contributors_by_score_empty(self, db_session) -> None:
        """Test top contributors with no scores."""
        result = AnalyticsRepository.get_top_contributors_by_score(db_session, limit=10)

        assert result == []

    def test_get_top_contributors_by_score_with_data(
        self, db_session, test_user, test_idea, create_votes
    ) -> None:
        """Test top contributors by vote score."""
        # Add votes to the test idea
        create_votes(test_idea.id, upvotes=5, downvotes=2)

        result = AnalyticsRepository.get_top_contributors_by_score(db_session, limit=10)

        assert len(result) >= 1
        # test_user should have score of 3 (5 upvotes - 2 downvotes)
        assert result[0]["user_id"] == test_user.id
        assert result[0]["count"] == 3  # net score

    def test_get_top_contributors_respects_limit(
        self, db_session, test_category, admin_user
    ) -> None:
        """Test that limit is respected."""
        from authentication.auth import get_password_hash

        # Create multiple users with ideas
        for i in range(15):
            user = db_models.User(
                email=f"user{i}@example.com",
                username=f"user{i}",
                display_name=f"User {i}",
                hashed_password=get_password_hash("password"),
                is_active=True,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            idea = db_models.Idea(
                title=f"Idea {i}",
                description="Test idea description",
                category_id=test_category.id,
                user_id=user.id,
                status=db_models.IdeaStatus.APPROVED,
            )
            db_session.add(idea)
        db_session.commit()

        result = AnalyticsRepository.get_top_contributors_by_ideas(db_session, limit=10)

        assert len(result) == 10
