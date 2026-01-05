"""
Quality repository for database operations.
"""

from sqlalchemy.orm import Session

from repositories.base import BaseRepository
from repositories.db_models import CategoryQuality, Quality


class QualityRepository(BaseRepository[Quality]):
    """Repository for Quality entity database operations."""

    def __init__(self, db: Session):
        """
        Initialize quality repository.

        Args:
            db: Database session
        """
        super().__init__(Quality, db)

    def get_by_key(self, key: str) -> Quality | None:
        """
        Get quality by unique key.

        Args:
            key: Quality key (e.g., 'community_benefit')

        Returns:
            Quality if found, None otherwise
        """
        return self.db.query(Quality).filter(Quality.key == key).first()

    def get_all_active(self) -> list[Quality]:
        """
        Get all active qualities ordered by display_order.

        Returns:
            List of active qualities
        """
        return (
            self.db.query(Quality)
            .filter(Quality.is_active.is_(True))
            .order_by(Quality.display_order)
            .all()
        )

    def get_defaults(self) -> list[Quality]:
        """
        Get all default qualities (apply to all categories).

        Returns:
            List of default active qualities
        """
        return (
            self.db.query(Quality)
            .filter(Quality.is_active.is_(True), Quality.is_default.is_(True))
            .order_by(Quality.display_order)
            .all()
        )

    def get_for_category(self, category_id: int) -> list[Quality]:
        """
        Get qualities available for a specific category.

        Logic:
        1. Include all default qualities UNLESS explicitly disabled for this category
        2. Include non-default qualities IF explicitly enabled for this category

        Args:
            category_id: Category ID

        Returns:
            List of qualities available for this category
        """
        # Get explicit overrides for this category
        overrides = (
            self.db.query(CategoryQuality)
            .filter(CategoryQuality.category_id == category_id)
            .all()
        )

        override_map = {co.quality_id: co for co in overrides}

        # Get all active qualities
        all_qualities = self.get_all_active()

        result = []
        for quality in all_qualities:
            override = override_map.get(quality.id)

            if override:
                # Explicit override exists
                if override.is_enabled:
                    result.append(quality)
            elif quality.is_default:
                # No override, but it's a default quality
                result.append(quality)
            # Non-default without explicit enable = not included

        # Sort by category-specific order if available, else default order
        def sort_key(q: Quality) -> int:
            override = override_map.get(q.id)
            if override and override.display_order is not None:
                return override.display_order
            return q.display_order

        return sorted(result, key=sort_key)

    def get_by_ids(self, quality_ids: list[int]) -> list[Quality]:
        """
        Get multiple qualities by their IDs.

        Args:
            quality_ids: List of quality IDs

        Returns:
            List of qualities (active ones only)
        """
        if not quality_ids:
            return []
        return (
            self.db.query(Quality)
            .filter(Quality.id.in_(quality_ids), Quality.is_active.is_(True))
            .all()
        )

    def get_by_keys(self, keys: list[str]) -> list[Quality]:
        """
        Get multiple qualities by their keys.

        Args:
            keys: List of quality keys (e.g., ['community_benefit', 'urgent'])

        Returns:
            List of qualities (active ones only)
        """
        if not keys:
            return []
        return (
            self.db.query(Quality)
            .filter(Quality.key.in_(keys), Quality.is_active.is_(True))
            .all()
        )
