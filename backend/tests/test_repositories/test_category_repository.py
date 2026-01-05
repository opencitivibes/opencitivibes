"""Tests for CategoryRepository."""

import repositories.db_models as db_models
from repositories.category_repository import CategoryRepository


class TestCategoryRepository:
    """Test cases for CategoryRepository."""

    def test_get_all_with_statistics_empty(self, db_session, test_category):
        """Get statistics for category with no ideas."""
        repo = CategoryRepository(db_session)
        stats = repo.get_all_with_statistics()

        assert len(stats) >= 1

        # Find test category in results
        test_cat_stats = next(
            (s for s in stats if s["category_id"] == test_category.id), None
        )
        assert test_cat_stats is not None
        assert test_cat_stats["total_ideas"] == 0
        assert test_cat_stats["approved_ideas"] == 0
        assert test_cat_stats["pending_ideas"] == 0
        assert test_cat_stats["rejected_ideas"] == 0

    def test_get_all_with_statistics_with_ideas(
        self, db_session, test_user, test_category
    ):
        """Get statistics with various idea statuses."""
        # Create ideas with different statuses
        approved = db_models.Idea(
            title="Approved Idea",
            description="Approved idea description that is long enough.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        pending = db_models.Idea(
            title="Pending Idea",
            description="Pending idea description that is long enough.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.PENDING,
        )
        rejected = db_models.Idea(
            title="Rejected Idea",
            description="Rejected idea description that is long enough.",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.REJECTED,
        )
        db_session.add(approved)
        db_session.add(pending)
        db_session.add(rejected)
        db_session.commit()

        repo = CategoryRepository(db_session)
        stats = repo.get_all_with_statistics()

        # Find test category in results
        test_cat_stats = next(
            (s for s in stats if s["category_id"] == test_category.id), None
        )
        assert test_cat_stats is not None
        assert test_cat_stats["total_ideas"] == 3
        assert test_cat_stats["approved_ideas"] == 1
        assert test_cat_stats["pending_ideas"] == 1
        assert test_cat_stats["rejected_ideas"] == 1
        assert test_cat_stats["category_name_en"] == test_category.name_en
        assert test_cat_stats["category_name_fr"] == test_category.name_fr

    def test_get_all_with_statistics_multiple_categories(self, db_session, test_user):
        """Get statistics for multiple categories."""
        # Create categories
        cat1 = db_models.Category(
            name_en="Category 1",
            name_fr="Catégorie 1",
            description_en="Description 1",
            description_fr="Description 1 FR",
        )
        cat2 = db_models.Category(
            name_en="Category 2",
            name_fr="Catégorie 2",
            description_en="Description 2",
            description_fr="Description 2 FR",
        )
        db_session.add(cat1)
        db_session.add(cat2)
        db_session.commit()

        # Add ideas to first category
        idea1 = db_models.Idea(
            title="Idea 1",
            description="Idea 1 description that is long enough.",
            category_id=cat1.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.APPROVED,
        )
        db_session.add(idea1)
        db_session.commit()

        repo = CategoryRepository(db_session)
        stats = repo.get_all_with_statistics()

        # Should have at least 2 categories
        assert len(stats) >= 2

        # Verify cat1 has ideas
        cat1_stats = next((s for s in stats if s["category_id"] == cat1.id), None)
        assert cat1_stats is not None
        assert cat1_stats["total_ideas"] == 1

        # Verify cat2 has no ideas
        cat2_stats = next((s for s in stats if s["category_id"] == cat2.id), None)
        assert cat2_stats is not None
        assert cat2_stats["total_ideas"] == 0

    def test_get_by_name_english(self, db_session, test_category):
        """Get category by English name."""
        repo = CategoryRepository(db_session)
        category = repo.get_by_name(name_en=test_category.name_en)

        assert category is not None
        assert category.id == test_category.id
        assert category.name_en == test_category.name_en

    def test_get_by_name_french(self, db_session, test_category):
        """Get category by French name."""
        repo = CategoryRepository(db_session)
        category = repo.get_by_name(name_fr=test_category.name_fr)

        assert category is not None
        assert category.id == test_category.id
        assert category.name_fr == test_category.name_fr

    def test_get_by_name_not_found(self, db_session):
        """Get category returns None when not found."""
        repo = CategoryRepository(db_session)
        category = repo.get_by_name(name_en="Nonexistent Category")
        assert category is None

    def test_get_by_name_no_params(self, db_session):
        """Get category returns None when no parameters provided."""
        repo = CategoryRepository(db_session)
        category = repo.get_by_name()
        assert category is None

    def test_get_by_name_prefers_english(self, db_session, test_category):
        """Get category prefers English name when both provided."""
        repo = CategoryRepository(db_session)
        category = repo.get_by_name(
            name_en=test_category.name_en, name_fr="Wrong French Name"
        )

        # Should find by English name even though French is wrong
        assert category is not None
        assert category.id == test_category.id
