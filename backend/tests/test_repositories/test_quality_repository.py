"""Tests for QualityRepository."""

import pytest

import repositories.db_models as db_models
from repositories.quality_repository import QualityRepository


@pytest.fixture
def test_quality(db_session) -> db_models.Quality:
    """Create a default test quality."""
    quality = db_models.Quality(
        key="test_quality",
        name_en="Test Quality",
        name_fr="Qualité Test",
        description_en="A test quality description",
        description_fr="Une description de qualité test",
        icon="star",
        color="blue",
        is_default=True,
        is_active=True,
        display_order=1,
    )
    db_session.add(quality)
    db_session.commit()
    db_session.refresh(quality)
    return quality


@pytest.fixture
def inactive_quality(db_session) -> db_models.Quality:
    """Create an inactive quality."""
    quality = db_models.Quality(
        key="inactive_quality",
        name_en="Inactive Quality",
        name_fr="Qualité Inactive",
        is_default=True,
        is_active=False,
        display_order=5,
    )
    db_session.add(quality)
    db_session.commit()
    db_session.refresh(quality)
    return quality


@pytest.fixture
def non_default_quality(db_session) -> db_models.Quality:
    """Create a non-default quality."""
    quality = db_models.Quality(
        key="non_default_quality",
        name_en="Non-Default Quality",
        name_fr="Qualité Non-Default",
        is_default=False,
        is_active=True,
        display_order=10,
    )
    db_session.add(quality)
    db_session.commit()
    db_session.refresh(quality)
    return quality


@pytest.fixture
def multiple_qualities(db_session) -> list[db_models.Quality]:
    """Create multiple qualities with different display orders."""
    qualities = []
    for i, (key, order) in enumerate(
        [("quality_c", 3), ("quality_a", 1), ("quality_b", 2)]
    ):
        quality = db_models.Quality(
            key=key,
            name_en=f"Quality {key.upper()}",
            name_fr=f"Qualité {key.upper()}",
            is_default=True,
            is_active=True,
            display_order=order,
        )
        db_session.add(quality)
        qualities.append(quality)
    db_session.commit()
    for q in qualities:
        db_session.refresh(q)
    return qualities


class TestQualityRepository:
    """Test cases for QualityRepository."""

    def test_get_by_id(self, db_session, test_quality):
        """Get quality by ID."""
        repo = QualityRepository(db_session)
        result = repo.get_by_id(test_quality.id)

        assert result is not None
        assert result.id == test_quality.id
        assert result.key == "test_quality"

    def test_get_by_id_not_found(self, db_session):
        """Get quality by ID returns None when not found."""
        repo = QualityRepository(db_session)
        result = repo.get_by_id(99999)
        assert result is None

    def test_get_by_key(self, db_session, test_quality):
        """Get quality by unique key."""
        repo = QualityRepository(db_session)
        result = repo.get_by_key("test_quality")

        assert result is not None
        assert result.id == test_quality.id
        assert result.name_en == "Test Quality"

    def test_get_by_key_not_found(self, db_session):
        """Get quality by key returns None when not found."""
        repo = QualityRepository(db_session)
        result = repo.get_by_key("nonexistent_key")
        assert result is None

    def test_get_all_active(self, db_session, test_quality, inactive_quality):
        """Get all active qualities, excluding inactive ones."""
        repo = QualityRepository(db_session)
        results = repo.get_all_active()

        assert len(results) == 1
        assert results[0].id == test_quality.id
        assert all(q.is_active for q in results)

    def test_get_all_active_ordered_by_display_order(
        self, db_session, multiple_qualities
    ):
        """Get all active qualities ordered by display_order."""
        repo = QualityRepository(db_session)
        results = repo.get_all_active()

        assert len(results) == 3
        # Should be ordered: quality_a (1), quality_b (2), quality_c (3)
        assert results[0].key == "quality_a"
        assert results[1].key == "quality_b"
        assert results[2].key == "quality_c"

    def test_get_defaults(self, db_session, test_quality, non_default_quality):
        """Get only default qualities."""
        repo = QualityRepository(db_session)
        results = repo.get_defaults()

        assert len(results) == 1
        assert results[0].id == test_quality.id
        assert all(q.is_default for q in results)

    def test_get_defaults_excludes_inactive(
        self, db_session, test_quality, inactive_quality
    ):
        """Get defaults excludes inactive default qualities."""
        repo = QualityRepository(db_session)
        results = repo.get_defaults()

        assert len(results) == 1
        assert results[0].id == test_quality.id

    def test_get_for_category_returns_defaults(
        self, db_session, test_category, test_quality
    ):
        """Get qualities for category returns defaults when no overrides."""
        repo = QualityRepository(db_session)
        results = repo.get_for_category(test_category.id)

        assert len(results) == 1
        assert results[0].id == test_quality.id

    def test_get_for_category_respects_disabled_override(
        self, db_session, test_category, test_quality
    ):
        """Get qualities for category excludes explicitly disabled defaults."""
        # Create override to disable the default quality
        override = db_models.CategoryQuality(
            category_id=test_category.id,
            quality_id=test_quality.id,
            is_enabled=False,
        )
        db_session.add(override)
        db_session.commit()

        repo = QualityRepository(db_session)
        results = repo.get_for_category(test_category.id)

        assert len(results) == 0

    def test_get_for_category_includes_enabled_non_default(
        self, db_session, test_category, non_default_quality
    ):
        """Get qualities for category includes explicitly enabled non-defaults."""
        # Create override to enable the non-default quality
        override = db_models.CategoryQuality(
            category_id=test_category.id,
            quality_id=non_default_quality.id,
            is_enabled=True,
        )
        db_session.add(override)
        db_session.commit()

        repo = QualityRepository(db_session)
        results = repo.get_for_category(test_category.id)

        assert len(results) == 1
        assert results[0].id == non_default_quality.id

    def test_get_for_category_respects_override_display_order(
        self, db_session, test_category, multiple_qualities
    ):
        """Get qualities for category uses override display_order when available."""
        # Create override with custom display order for quality_c
        override = db_models.CategoryQuality(
            category_id=test_category.id,
            quality_id=multiple_qualities[0].id,  # quality_c has display_order=3
            is_enabled=True,
            display_order=0,  # Override to be first
        )
        db_session.add(override)
        db_session.commit()

        repo = QualityRepository(db_session)
        results = repo.get_for_category(test_category.id)

        # quality_c should now be first due to override display_order=0
        assert results[0].key == "quality_c"

    def test_get_by_ids(self, db_session, multiple_qualities):
        """Get multiple qualities by their IDs."""
        repo = QualityRepository(db_session)
        ids = [multiple_qualities[0].id, multiple_qualities[2].id]
        results = repo.get_by_ids(ids)

        assert len(results) == 2
        result_ids = [q.id for q in results]
        assert multiple_qualities[0].id in result_ids
        assert multiple_qualities[2].id in result_ids

    def test_get_by_ids_empty_list(self, db_session):
        """Get by IDs with empty list returns empty list."""
        repo = QualityRepository(db_session)
        results = repo.get_by_ids([])
        assert results == []

    def test_get_by_ids_filters_inactive(
        self, db_session, test_quality, inactive_quality
    ):
        """Get by IDs only returns active qualities."""
        repo = QualityRepository(db_session)
        results = repo.get_by_ids([test_quality.id, inactive_quality.id])

        assert len(results) == 1
        assert results[0].id == test_quality.id

    def test_create_quality(self, db_session):
        """Create a new quality."""
        repo = QualityRepository(db_session)
        quality = db_models.Quality(
            key="new_quality",
            name_en="New Quality",
            name_fr="Nouvelle Qualité",
            is_default=True,
            is_active=True,
            display_order=1,
        )
        result = repo.create(quality)

        assert result.id is not None
        assert result.key == "new_quality"

        # Verify it's in the database
        fetched = repo.get_by_key("new_quality")
        assert fetched is not None

    def test_count(self, db_session, multiple_qualities):
        """Count total qualities."""
        repo = QualityRepository(db_session)
        count = repo.count()
        assert count == 3
