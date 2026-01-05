"""
Unit tests for QualityService.
"""

from sqlalchemy.orm import Session

from repositories.db_models import (
    Category,
    CategoryQuality,
    Idea,
    Quality,
    User,
    Vote,
    VoteQuality,
    VoteType,
)
from services.quality_service import QualityService


class TestGetQualitiesForCategory:
    """Tests for get_qualities_for_category method."""

    def test_returns_default_qualities(
        self, db_session: Session, test_category: Category
    ):
        """Should return default qualities for any category."""
        # Create default quality
        quality = Quality(
            key="test_quality",
            name_en="Test",
            name_fr="Test FR",
            is_default=True,
            is_active=True,
            display_order=1,
        )
        db_session.add(quality)
        db_session.commit()

        result = QualityService.get_qualities_for_category(db_session, test_category.id)

        assert len(result) == 1
        assert result[0].key == "test_quality"

    def test_excludes_inactive_qualities(
        self, db_session: Session, test_category: Category
    ):
        """Should not return inactive qualities."""
        quality = Quality(
            key="inactive_quality",
            name_en="Inactive",
            name_fr="Inactive FR",
            is_default=True,
            is_active=False,
            display_order=1,
        )
        db_session.add(quality)
        db_session.commit()

        result = QualityService.get_qualities_for_category(db_session, test_category.id)

        assert len(result) == 0

    def test_includes_non_default_when_enabled(
        self, db_session: Session, test_category: Category
    ):
        """Should include non-default quality when enabled for category."""
        quality = Quality(
            key="special_quality",
            name_en="Special",
            name_fr="Special FR",
            is_default=False,
            is_active=True,
            display_order=1,
        )
        db_session.add(quality)
        db_session.flush()

        # Enable for this category
        override = CategoryQuality(
            category_id=test_category.id,
            quality_id=quality.id,
            is_enabled=True,
        )
        db_session.add(override)
        db_session.commit()

        result = QualityService.get_qualities_for_category(db_session, test_category.id)

        assert len(result) == 1
        assert result[0].key == "special_quality"

    def test_excludes_default_when_disabled(
        self, db_session: Session, test_category: Category
    ):
        """Should exclude default quality when disabled for category."""
        quality = Quality(
            key="disabled_quality",
            name_en="Disabled",
            name_fr="Disabled FR",
            is_default=True,
            is_active=True,
            display_order=1,
        )
        db_session.add(quality)
        db_session.flush()

        # Disable for this category
        override = CategoryQuality(
            category_id=test_category.id,
            quality_id=quality.id,
            is_enabled=False,
        )
        db_session.add(override)
        db_session.commit()

        result = QualityService.get_qualities_for_category(db_session, test_category.id)

        assert len(result) == 0


class TestGetAllDefaultQualities:
    """Tests for get_all_default_qualities method."""

    def test_returns_only_defaults(self, db_session: Session):
        """Should return only default qualities."""
        default = Quality(
            key="default",
            name_en="Default",
            name_fr="Default FR",
            is_default=True,
            is_active=True,
            display_order=1,
        )
        non_default = Quality(
            key="non_default",
            name_en="Non Default",
            name_fr="Non Default FR",
            is_default=False,
            is_active=True,
            display_order=2,
        )
        db_session.add_all([default, non_default])
        db_session.commit()

        result = QualityService.get_all_default_qualities(db_session)

        assert len(result) == 1
        assert result[0].key == "default"

    def test_returns_empty_when_no_defaults(self, db_session: Session):
        """Should return empty list when no default qualities exist."""
        result = QualityService.get_all_default_qualities(db_session)
        assert result == []


class TestGetQualityCountsForIdea:
    """Tests for get_quality_counts_for_idea method."""

    def test_returns_empty_for_idea_without_votes(
        self, db_session: Session, test_idea: Idea
    ):
        """Should return empty counts for idea with no quality votes."""
        result = QualityService.get_quality_counts_for_idea(db_session, test_idea.id)

        assert result.counts == []
        assert result.total_votes_with_qualities == 0

    def test_counts_qualities_correctly(
        self, db_session: Session, test_idea: Idea, test_user: User
    ):
        """Should count qualities from upvotes correctly."""
        # Create quality
        quality = Quality(
            key="test_quality",
            name_en="Test",
            name_fr="Test FR",
            is_default=True,
            is_active=True,
            display_order=1,
        )
        db_session.add(quality)
        db_session.flush()

        # Create voter (different from idea author)
        voter = User(
            email="voter@test.com",
            username="voter",
            display_name="Voter",
            hashed_password="hash",
        )
        db_session.add(voter)
        db_session.flush()

        # Create upvote with quality
        vote = Vote(
            idea_id=test_idea.id,
            user_id=voter.id,
            vote_type=VoteType.UPVOTE,
        )
        db_session.add(vote)
        db_session.flush()

        vote_quality = VoteQuality(
            vote_id=vote.id,
            quality_id=quality.id,
        )
        db_session.add(vote_quality)
        db_session.commit()

        result = QualityService.get_quality_counts_for_idea(db_session, test_idea.id)

        assert len(result.counts) == 1
        assert result.counts[0].quality_id == quality.id
        assert result.counts[0].quality_key == "test_quality"
        assert result.counts[0].count == 1
        assert result.total_votes_with_qualities == 1


class TestValidateQualityIds:
    """Tests for validate_quality_ids method."""

    def test_returns_empty_for_empty_input(
        self, db_session: Session, test_category: Category
    ):
        """Should return empty list for empty input."""
        result = QualityService.validate_quality_ids(db_session, [], test_category.id)
        assert result == []

    def test_filters_invalid_ids(self, db_session: Session, test_category: Category):
        """Should filter out invalid quality IDs."""
        quality = Quality(
            key="valid",
            name_en="Valid",
            name_fr="Valid FR",
            is_default=True,
            is_active=True,
            display_order=1,
        )
        db_session.add(quality)
        db_session.commit()

        # Pass valid ID and invalid ID
        result = QualityService.validate_quality_ids(
            db_session, [quality.id, 9999], test_category.id
        )

        assert result == [quality.id]

    def test_returns_valid_ids_only(self, db_session: Session, test_category: Category):
        """Should return only valid quality IDs for category."""
        quality1 = Quality(
            key="q1",
            name_en="Q1",
            name_fr="Q1 FR",
            is_default=True,
            is_active=True,
            display_order=1,
        )
        quality2 = Quality(
            key="q2",
            name_en="Q2",
            name_fr="Q2 FR",
            is_default=True,
            is_active=True,
            display_order=2,
        )
        db_session.add_all([quality1, quality2])
        db_session.commit()

        result = QualityService.validate_quality_ids(
            db_session, [quality1.id, quality2.id], test_category.id
        )

        assert len(result) == 2
        assert quality1.id in result
        assert quality2.id in result

    def test_excludes_disabled_for_category(
        self, db_session: Session, test_category: Category
    ):
        """Should exclude qualities disabled for category."""
        quality = Quality(
            key="disabled",
            name_en="Disabled",
            name_fr="Disabled FR",
            is_default=True,
            is_active=True,
            display_order=1,
        )
        db_session.add(quality)
        db_session.flush()

        # Disable for this category
        override = CategoryQuality(
            category_id=test_category.id,
            quality_id=quality.id,
            is_enabled=False,
        )
        db_session.add(override)
        db_session.commit()

        result = QualityService.validate_quality_ids(
            db_session, [quality.id], test_category.id
        )

        assert result == []
