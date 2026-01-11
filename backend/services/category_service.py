"""
Category Service

Handles category management operations with caching.
"""

import time
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models.schemas as schemas
import repositories.db_models as db_models
from models.exceptions import (
    AlreadyExistsException,
    BusinessRuleException,
    NotFoundException,
)
from repositories.category_repository import CategoryRepository


class CategoryService:
    """
    Service for managing categories with in-memory caching.

    Note: The cache is designed for single-worker deployments.
    For multi-worker production deployments, consider using Redis or memcached.
    The cache operations are not thread-safe in concurrent async contexts,
    but race conditions are benign (worst case: cache miss, fresh DB fetch).
    """

    # Cache storage: {cache_key: (data, timestamp)}
    _cache: dict[str, tuple[Any, float]] = {}
    _cache_ttl: float = 300.0  # 5 minutes in seconds

    # Cache keys
    _CACHE_ALL_CATEGORIES = "all_categories"
    _CACHE_ALL_WITH_STATS = "all_categories_with_stats"

    @classmethod
    def _get_from_cache(cls, key: str) -> Any | None:
        """
        Get data from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached data or None if expired/missing
        """
        if key not in cls._cache:
            return None

        data, cached_time = cls._cache[key]
        if time.time() - cached_time > cls._cache_ttl:
            # Cache expired
            del cls._cache[key]
            return None

        return data

    @classmethod
    def _set_cache(cls, key: str, data: Any) -> None:
        """
        Store data in cache.

        Args:
            key: Cache key
            data: Data to cache
        """
        cls._cache[key] = (data, time.time())

    @classmethod
    def invalidate_cache(cls) -> None:
        """Invalidate all category caches after mutations."""
        cls._cache.clear()

    @staticmethod
    def get_all_categories(db: Session) -> list[db_models.Category]:
        """
        Get all categories with caching.

        Args:
            db: Database session

        Returns:
            List of all categories
        """

        # Check cache first
        cached = CategoryService._get_from_cache(CategoryService._CACHE_ALL_CATEGORIES)
        if cached is not None:
            return cached

        # Cache miss - fetch from database
        category_repo = CategoryRepository(db)
        categories = category_repo.get_all()

        # Store in cache
        CategoryService._set_cache(CategoryService._CACHE_ALL_CATEGORIES, categories)

        return categories

    @staticmethod
    def get_category_by_id(db: Session, category_id: int) -> db_models.Category:
        """
        Get category by ID.

        Args:
            db: Database session
            category_id: Category ID

        Returns:
            Category object

        Raises:
            NotFoundException: If category does not exist
        """
        category_repo = CategoryRepository(db)
        category = category_repo.get_by_id(category_id)
        if category is None:
            raise NotFoundException(f"Category with ID {category_id} not found")
        return category

    @staticmethod
    def create_category(
        db: Session, category: schemas.CategoryCreate
    ) -> db_models.Category:
        """
        Create a new category.

        Args:
            db: Database session
            category: Category data

        Returns:
            Created category

        Raises:
            AlreadyExistsException: If category creation fails
        """
        category_repo = CategoryRepository(db)
        db_category = db_models.Category(**category.model_dump())
        try:
            category_repo.add(db_category)
            category_repo.commit()
            category_repo.refresh(db_category)

            # Invalidate cache after mutation
            CategoryService.invalidate_cache()

            return db_category
        except IntegrityError:
            category_repo.rollback()
            raise AlreadyExistsException("Category with this name already exists")

    @staticmethod
    def update_category(
        db: Session, category_id: int, category_update: schemas.CategoryUpdate
    ) -> db_models.Category:
        """
        Update an existing category.

        Args:
            db: Database session
            category_id: Category ID
            category_update: Updated category data

        Returns:
            Updated category

        Raises:
            NotFoundException: If category not found
        """
        category_repo = CategoryRepository(db)
        db_category = category_repo.get_by_id(category_id)
        if not db_category:
            raise NotFoundException("Category not found")

        # Update only provided fields
        update_data = category_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_category, field, value)

        category_repo.commit()
        category_repo.refresh(db_category)

        # Invalidate cache after mutation
        CategoryService.invalidate_cache()

        return db_category

    @staticmethod
    def delete_category(db: Session, category_id: int) -> bool:
        """
        Delete a category.

        Args:
            db: Database session
            category_id: Category ID

        Returns:
            True if deleted successfully

        Raises:
            NotFoundException: If category not found
            BusinessRuleException: If category has associated ideas
        """
        from repositories.idea_repository import IdeaRepository

        category_repo = CategoryRepository(db)
        db_category = category_repo.get_by_id(category_id)
        if not db_category:
            raise NotFoundException("Category not found")

        # Check if category has any ideas
        idea_repo = IdeaRepository(db)
        ideas_count = idea_repo.count_by_category(category_id)

        if ideas_count > 0:
            raise BusinessRuleException(
                f"Cannot delete category with {ideas_count} associated ideas"
            )

        category_repo.delete(db_category)

        # Invalidate cache after mutation
        CategoryService.invalidate_cache()

        return True

    @staticmethod
    def get_category_statistics(
        db: Session, category_id: int
    ) -> schemas.CategoryStatistics:
        """
        Get statistics for a category.

        Args:
            db: Database session
            category_id: Category ID

        Returns:
            CategoryStatistics schema with category statistics
        """
        from repositories.idea_repository import IdeaRepository

        category = CategoryService.get_category_by_id(db, category_id)
        if not category:
            raise NotFoundException("Category not found")

        idea_repo = IdeaRepository(db)
        total_ideas = idea_repo.count_by_category(category_id)
        approved_ideas = idea_repo.count_by_category(
            category_id, db_models.IdeaStatus.APPROVED
        )
        pending_ideas = idea_repo.count_by_category(
            category_id, db_models.IdeaStatus.PENDING
        )
        rejected_ideas = idea_repo.count_by_category(
            category_id, db_models.IdeaStatus.REJECTED
        )

        return schemas.CategoryStatistics(
            category_id=category_id,
            category_name_en=str(category.name_en),
            category_name_fr=str(category.name_fr),
            total_ideas=total_ideas,
            approved_ideas=approved_ideas,
            pending_ideas=pending_ideas,
            rejected_ideas=rejected_ideas,
        )

    @staticmethod
    def get_all_categories_with_statistics(
        db: Session,
    ) -> list[schemas.CategoryStatistics]:
        """
        Get all categories with their statistics.

        Uses optimized single query with GROUP BY and caching.

        Args:
            db: Database session

        Returns:
            List of CategoryStatistics schemas
        """
        # Check cache first
        cached = CategoryService._get_from_cache(CategoryService._CACHE_ALL_WITH_STATS)
        if cached is not None:
            return [schemas.CategoryStatistics(**item) for item in cached]

        # Cache miss - fetch from database

        category_repo = CategoryRepository(db)
        result = category_repo.get_all_with_statistics()

        # Store in cache (store raw dicts for cache efficiency)
        CategoryService._set_cache(CategoryService._CACHE_ALL_WITH_STATS, result)

        return [schemas.CategoryStatistics(**item) for item in result]
