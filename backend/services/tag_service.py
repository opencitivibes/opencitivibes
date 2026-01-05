"""
Tag service for business logic with caching.
"""

import time
from typing import Any

from sqlalchemy.orm import Session

import models.schemas as schemas
import repositories.db_models as db_models
from models.exceptions import BusinessRuleException, NotFoundException
from repositories.idea_repository import IdeaRepository
from repositories.tag_repository import IdeaTagRepository, TagRepository


class TagService:
    """
    Service for tag-related business logic with caching.

    Note: The cache is designed for single-worker deployments.
    For multi-worker production deployments, consider using Redis or memcached.
    The cache operations are not thread-safe in concurrent async contexts,
    but race conditions are benign (worst case: cache miss, fresh DB fetch).
    """

    # Cache storage: {cache_key: (data, timestamp)}
    _cache: dict[str, tuple[Any, float]] = {}
    _cache_ttl: float = 300.0  # 5 minutes in seconds

    @classmethod
    def _get_cache_key(cls, prefix: str, *args: Any) -> str:
        """Generate cache key from prefix and arguments."""
        return f"{prefix}:{':'.join(str(a) for a in args)}"

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
    def invalidate_popular_cache(cls) -> None:
        """Invalidate popular tags cache after tag changes."""
        # Clear all cache entries starting with 'popular'
        keys_to_delete = [k for k in cls._cache if k.startswith("popular")]
        for key in keys_to_delete:
            del cls._cache[key]

    @staticmethod
    def get_all_tags(
        db: Session, skip: int = 0, limit: int = 100
    ) -> list[db_models.Tag]:
        """
        Get all tags with pagination.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of tags
        """
        tag_repo = TagRepository(db)
        return tag_repo.get_all(skip=skip, limit=limit)

    @staticmethod
    def get_tag_by_id(db: Session, tag_id: int) -> db_models.Tag:
        """
        Get a tag by ID.

        Args:
            db: Database session
            tag_id: Tag ID

        Returns:
            Tag entity

        Raises:
            NotFoundException: If tag not found
        """
        tag_repo = TagRepository(db)
        tag = tag_repo.get_by_id(tag_id)

        if not tag:
            raise NotFoundException(f"Tag with ID {tag_id} not found")

        return tag

    @staticmethod
    def get_tag_by_name(db: Session, name: str) -> db_models.Tag:
        """
        Get a tag by its exact name.

        Args:
            db: Database session
            name: Tag name (will be normalized to lowercase)

        Returns:
            Tag entity

        Raises:
            NotFoundException: If tag not found
        """
        tag_repo = TagRepository(db)
        tag = tag_repo.get_by_name(name)

        if not tag:
            raise NotFoundException(f"Tag '{name}' not found")

        return tag

    @staticmethod
    def search_tags(db: Session, query: str, limit: int = 10) -> list[db_models.Tag]:
        """
        Search tags by name (for autocomplete).

        Args:
            db: Database session
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of matching tags
        """
        if not query or len(query.strip()) < 1:
            return []

        tag_repo = TagRepository(db)
        return tag_repo.search_tags(query, limit)

    @staticmethod
    def get_popular_tags(
        db: Session, limit: int = 20, min_ideas: int = 1
    ) -> list[schemas.TagWithCount]:
        """
        Get most popular tags with caching.

        Args:
            db: Database session
            limit: Maximum number of tags to return
            min_ideas: Minimum number of ideas required

        Returns:
            List of tags with idea counts
        """
        # Check cache first
        cache_key = TagService._get_cache_key("popular", limit, min_ideas)
        cached = TagService._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # Cache miss - fetch from database
        tag_repo = TagRepository(db)
        results = tag_repo.get_popular_tags(limit, min_ideas)

        # Convert to TagWithCount schema
        popular_tags = [
            schemas.TagWithCount(
                id=tag.id,
                name=tag.name,
                display_name=tag.display_name,
                created_at=tag.created_at,
                idea_count=count,
            )
            for tag, count in results
        ]

        # Store in cache
        TagService._set_cache(cache_key, popular_tags)

        return popular_tags

    @staticmethod
    def get_tag_statistics(db: Session, tag_id: int) -> schemas.TagStatistics:
        """
        Get statistics for a tag.

        Args:
            db: Database session
            tag_id: Tag ID

        Returns:
            Tag statistics

        Raises:
            NotFoundException: If tag not found
        """
        tag_repo = TagRepository(db)
        stats = tag_repo.get_tag_statistics(tag_id)

        if not stats:
            raise NotFoundException(f"Tag with ID {tag_id} not found")

        return schemas.TagStatistics(
            tag=schemas.Tag(
                id=stats["tag"].id,
                name=stats["tag"].name,
                display_name=stats["tag"].display_name,
                created_at=stats["tag"].created_at,
            ),
            total_ideas=stats["total_ideas"],
            approved_ideas=stats["approved_ideas"],
            pending_ideas=stats["pending_ideas"],
        )

    @staticmethod
    def create_tag(db: Session, tag_data: schemas.TagCreate) -> db_models.Tag:
        """
        Create a new tag or return existing one.

        Args:
            db: Database session
            tag_data: Tag creation data

        Returns:
            Tag entity (created or existing)

        Raises:
            BusinessRuleException: If tag name is invalid
        """
        # Validate tag name
        tag_name = tag_data.display_name.strip()
        if not tag_name or len(tag_name) < 2:
            raise BusinessRuleException("Tag name must be at least 2 characters")

        if len(tag_name) > 50:
            raise BusinessRuleException("Tag name must be at most 50 characters")

        tag_repo = TagRepository(db)
        tag = tag_repo.create_or_get_tag(tag_name)

        # Invalidate popular tags cache since tag usage may have changed
        TagService.invalidate_popular_cache()

        return tag

    @staticmethod
    def delete_tag(db: Session, tag_id: int) -> None:
        """
        Delete a tag (admin only).

        Args:
            db: Database session
            tag_id: Tag ID

        Raises:
            NotFoundException: If tag not found
            BusinessRuleException: If tag is still in use
        """
        tag_repo = TagRepository(db)
        tag = tag_repo.get_by_id(tag_id)

        if not tag:
            raise NotFoundException(f"Tag with ID {tag_id} not found")

        # Check if tag is in use
        stats = tag_repo.get_tag_statistics(tag_id)
        if stats and stats["total_ideas"] > 0:
            raise BusinessRuleException(
                f"Cannot delete tag '{tag.display_name}' - "
                f"it is used by {stats['total_ideas']} idea(s)"
            )

        tag_repo.delete(tag)

        # Invalidate popular tags cache
        TagService.invalidate_popular_cache()

    @staticmethod
    def delete_unused_tags(db: Session) -> int:
        """
        Delete all unused tags (cleanup operation).

        Args:
            db: Database session

        Returns:
            Number of tags deleted
        """
        tag_repo = TagRepository(db)
        count = tag_repo.delete_unused_tags()

        # Invalidate popular tags cache
        TagService.invalidate_popular_cache()

        return count

    @staticmethod
    def get_tags_for_idea(db: Session, idea_id: int) -> list[db_models.Tag]:
        """
        Get all tags for a specific idea.

        Args:
            db: Database session
            idea_id: Idea ID

        Returns:
            List of tags

        Raises:
            NotFoundException: If idea not found
        """
        # Verify idea exists
        idea_repo = IdeaRepository(db)
        idea = idea_repo.get_by_id(idea_id)
        if not idea:
            raise NotFoundException(f"Idea with ID {idea_id} not found")

        tag_repo = TagRepository(db)
        return tag_repo.get_tags_for_idea(idea_id)

    @staticmethod
    def add_tag_to_idea(db: Session, idea_id: int, tag_name: str) -> db_models.Tag:
        """
        Add a tag to an idea.

        Args:
            db: Database session
            idea_id: Idea ID
            tag_name: Tag name (will create if doesn't exist)

        Returns:
            The tag that was added

        Raises:
            NotFoundException: If idea not found
            BusinessRuleException: If tag name is invalid
        """
        # Verify idea exists
        idea_repo = IdeaRepository(db)
        idea = idea_repo.get_by_id(idea_id)
        if not idea:
            raise NotFoundException(f"Idea with ID {idea_id} not found")

        # Create or get tag
        tag = TagService.create_tag(db, schemas.TagCreate(display_name=tag_name))

        # Associate tag with idea
        idea_tag_repo = IdeaTagRepository(db)
        idea_tag_repo.add_tag_to_idea(idea_id, tag.id)

        # Invalidate popular tags cache
        TagService.invalidate_popular_cache()

        return tag

    @staticmethod
    def remove_tag_from_idea(db: Session, idea_id: int, tag_id: int) -> bool:
        """
        Remove a tag from an idea.

        Args:
            db: Database session
            idea_id: Idea ID
            tag_id: Tag ID

        Returns:
            True if removed, False if association didn't exist

        Raises:
            NotFoundException: If idea or tag not found
        """
        # Verify idea exists
        idea_repo = IdeaRepository(db)
        idea = idea_repo.get_by_id(idea_id)
        if not idea:
            raise NotFoundException(f"Idea with ID {idea_id} not found")

        # Verify tag exists
        tag_repo = TagRepository(db)
        tag = tag_repo.get_by_id(tag_id)
        if not tag:
            raise NotFoundException(f"Tag with ID {tag_id} not found")

        # Remove association
        idea_tag_repo = IdeaTagRepository(db)
        result = idea_tag_repo.remove_tag_from_idea(idea_id, tag_id)

        # Invalidate popular tags cache
        TagService.invalidate_popular_cache()

        return result

    @staticmethod
    def sync_idea_tags(
        db: Session, idea_id: int, tag_names: list[str]
    ) -> list[db_models.Tag]:
        """
        Sync tags for an idea (remove old, add new).

        Args:
            db: Database session
            idea_id: Idea ID
            tag_names: List of tag names

        Returns:
            List of current tags for the idea

        Raises:
            NotFoundException: If idea not found
        """
        # Verify idea exists
        idea_repo = IdeaRepository(db)
        idea = idea_repo.get_by_id(idea_id)
        if not idea:
            raise NotFoundException(f"Idea with ID {idea_id} not found")

        # Remove all existing tags
        idea_tag_repo = IdeaTagRepository(db)
        idea_tag_repo.remove_all_tags_from_idea(idea_id)

        # Add new tags
        tags = []
        for tag_name in tag_names:
            if tag_name and tag_name.strip():
                tag = TagService.create_tag(
                    db, schemas.TagCreate(display_name=tag_name)
                )
                idea_tag_repo.add_tag_to_idea(idea_id, tag.id)
                tags.append(tag)

        # Invalidate popular tags cache
        TagService.invalidate_popular_cache()

        return tags

    @staticmethod
    def get_ideas_by_tag(
        db: Session,
        tag_id: int,
        status_filter: db_models.IdeaStatus = db_models.IdeaStatus.APPROVED,
        skip: int = 0,
        limit: int = 20,
    ) -> list[int]:
        """
        Get idea IDs for a specific tag.

        Args:
            db: Database session
            tag_id: Tag ID
            status_filter: Filter by idea status
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of idea IDs

        Raises:
            NotFoundException: If tag not found
        """
        # Verify tag exists
        tag_repo = TagRepository(db)
        tag = tag_repo.get_by_id(tag_id)
        if not tag:
            raise NotFoundException(f"Tag with ID {tag_id} not found")

        idea_tag_repo = IdeaTagRepository(db)
        return idea_tag_repo.get_ideas_by_tag(tag_id, status_filter, skip, limit)

    @staticmethod
    def get_ideas_by_tag_full(
        db: Session,
        tag_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[schemas.IdeaWithScore]:
        """
        Get full ideas with scores for a specific tag.

        Args:
            db: Database session
            tag_id: Tag ID
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of ideas with scores

        Raises:
            NotFoundException: If tag not found
        """
        # Verify tag exists
        tag_repo = TagRepository(db)
        tag = tag_repo.get_by_id(tag_id)
        if not tag:
            raise NotFoundException(f"Tag with ID {tag_id} not found")

        # Get full ideas with scores using the repository
        return IdeaRepository(db).get_ideas_by_tag_with_scores(
            tag_id=tag_id,
            skip=skip,
            limit=limit,
        )
