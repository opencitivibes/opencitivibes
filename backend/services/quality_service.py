"""
Quality service for business logic.
"""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from models.exceptions import CategoryNotFoundException
from repositories.category_repository import CategoryRepository
from repositories.db_models import Quality
from repositories.quality_repository import QualityRepository
from repositories.vote_quality_repository import VoteQualityRepository

if TYPE_CHECKING:
    import models.schemas as schemas


class QualityService:
    """Service for quality-related business logic."""

    @staticmethod
    def get_qualities_for_category(db: Session, category_id: int) -> list[Quality]:
        """
        Get available qualities for a category.

        Returns default qualities + category-specific additions,
        minus any explicitly disabled for this category.

        Args:
            db: Database session
            category_id: Category ID

        Returns:
            List of qualities available for the category

        Raises:
            CategoryNotFoundException: If the category does not exist
        """
        # Validate category exists
        category_repo = CategoryRepository(db)
        category = category_repo.get_by_id(category_id)
        if not category:
            raise CategoryNotFoundException(f"Category with ID {category_id} not found")

        quality_repo = QualityRepository(db)
        return quality_repo.get_for_category(category_id)

    @staticmethod
    def get_all_default_qualities(db: Session) -> list[Quality]:
        """
        Get all default qualities (for when category is unknown).

        Args:
            db: Database session

        Returns:
            List of default active qualities
        """
        quality_repo = QualityRepository(db)
        return quality_repo.get_defaults()

    @staticmethod
    def get_quality_counts_for_idea(
        db: Session, idea_id: int
    ) -> "schemas.QualityCounts":
        """
        Get quality counts for an idea.

        Args:
            db: Database session
            idea_id: Idea ID

        Returns:
            QualityCounts schema with counts and total_votes_with_qualities
        """
        import models.schemas as schemas

        vote_quality_repo = VoteQualityRepository(db)

        counts = vote_quality_repo.get_detailed_counts_for_idea(idea_id)
        total = vote_quality_repo.count_votes_with_qualities(idea_id)

        return schemas.QualityCounts(
            counts=[schemas.QualityCount(**c) for c in counts],
            total_votes_with_qualities=total,
        )

    @staticmethod
    def validate_quality_ids(
        db: Session, quality_ids: list[int], category_id: int
    ) -> list[int]:
        """
        Validate that quality IDs are valid for the given category.

        Returns only valid IDs (filters out invalid ones silently).

        Args:
            db: Database session
            quality_ids: List of quality IDs to validate
            category_id: Category ID for validation

        Returns:
            List of valid quality IDs
        """
        if not quality_ids:
            return []

        valid_qualities = QualityService.get_qualities_for_category(db, category_id)
        valid_ids = {q.id for q in valid_qualities}

        return [qid for qid in quality_ids if qid in valid_ids]

    @staticmethod
    def keys_to_ids(db: Session, keys: list[str], category_id: int) -> list[int]:
        """
        Convert quality keys to IDs, validating against category.

        Args:
            db: Database session
            keys: List of quality keys (e.g., ['community_benefit', 'urgent'])
            category_id: Category ID for validation

        Returns:
            List of valid quality IDs
        """
        if not keys:
            return []

        quality_repo = QualityRepository(db)
        qualities = quality_repo.get_by_keys(keys)

        # Get valid IDs for this category
        valid_qualities = QualityService.get_qualities_for_category(db, category_id)
        valid_ids = {q.id for q in valid_qualities}

        return [q.id for q in qualities if q.id in valid_ids]

    @staticmethod
    def ids_to_keys(db: Session, quality_ids: list[int]) -> list[str]:
        """
        Convert quality IDs to keys.

        Args:
            db: Database session
            quality_ids: List of quality IDs

        Returns:
            List of quality keys
        """
        if not quality_ids:
            return []

        quality_repo = QualityRepository(db)
        qualities = quality_repo.get_by_ids(quality_ids)

        return [q.key for q in qualities]
