"""
Tag repository for database operations.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from repositories.base import BaseRepository
from repositories.db_models import Tag, IdeaTag, Idea, IdeaStatus


class TagRepository(BaseRepository[Tag]):
    """
    Repository for Tag entity operations.
    """

    def __init__(self, db: Session):
        """
        Initialize TagRepository.

        Args:
            db: Database session
        """
        super().__init__(Tag, db)

    def get_by_name(self, name: str) -> Optional[Tag]:
        """
        Get tag by normalized name.

        Args:
            name: Tag name (will be normalized to lowercase)

        Returns:
            Tag if found, None otherwise
        """
        normalized_name = name.lower().strip()
        return self.db.query(Tag).filter(Tag.name == normalized_name).first()

    def search_tags(self, query: str, limit: int = 10) -> List[Tag]:
        """
        Search tags by name (for autocomplete).

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching tags
        """
        search_term = f"%{query.lower()}%"
        return (
            self.db.query(Tag)
            .filter(Tag.name.like(search_term))
            .order_by(Tag.display_name)
            .limit(limit)
            .all()
        )

    def get_popular_tags(self, limit: int = 20, min_ideas: int = 1) -> List[tuple]:
        """
        Get most popular tags based on number of approved ideas.

        Args:
            limit: Maximum number of tags to return
            min_ideas: Minimum number of ideas required

        Returns:
            List of tuples (tag, idea_count)
        """
        results = (
            self.db.query(Tag, func.count(IdeaTag.id).label("idea_count"))
            .join(IdeaTag, Tag.id == IdeaTag.tag_id)
            .join(Idea, IdeaTag.idea_id == Idea.id)
            .filter(Idea.status == IdeaStatus.APPROVED)
            .group_by(Tag.id)
            .having(func.count(IdeaTag.id) >= min_ideas)
            .order_by(desc("idea_count"))
            .limit(limit)
            .all()
        )
        return results  # type: ignore[return-value]

    def get_tags_for_idea(self, idea_id: int) -> List[Tag]:
        """
        Get all tags associated with an idea.

        Args:
            idea_id: Idea ID

        Returns:
            List of tags
        """
        return (
            self.db.query(Tag)
            .join(IdeaTag, Tag.id == IdeaTag.tag_id)
            .filter(IdeaTag.idea_id == idea_id)
            .order_by(Tag.display_name)
            .all()
        )

    def create_or_get_tag(self, tag_name: str) -> Tag:
        """
        Create a new tag or get existing one by name.

        Args:
            tag_name: Tag name (original case)

        Returns:
            Tag entity (existing or newly created)
        """
        normalized_name = tag_name.lower().strip()

        # Check if tag exists
        existing_tag = self.get_by_name(normalized_name)
        if existing_tag:
            return existing_tag

        # Create new tag
        new_tag = Tag(name=normalized_name, display_name=tag_name.strip())
        return self.create(new_tag)

    def delete_unused_tags(self) -> int:
        """
        Delete tags that are not associated with any ideas.
        Useful for cleanup operations.

        Returns:
            Number of tags deleted
        """
        unused_tags = (
            self.db.query(Tag)
            .outerjoin(IdeaTag, Tag.id == IdeaTag.tag_id)
            .filter(IdeaTag.id.is_(None))
            .all()
        )

        count = len(unused_tags)
        for tag in unused_tags:
            self.delete(tag)

        return count

    def get_tag_statistics(self, tag_id: int) -> Optional[dict]:
        """
        Get statistics for a specific tag.

        Args:
            tag_id: Tag ID

        Returns:
            Dictionary with tag statistics or None if tag not found
        """
        tag = self.get_by_id(tag_id)
        if not tag:
            return None

        # Count total ideas
        total_ideas = (
            self.db.query(func.count(IdeaTag.id))
            .filter(IdeaTag.tag_id == tag_id)
            .scalar()
        )

        # Count approved ideas
        approved_ideas = (
            self.db.query(func.count(IdeaTag.id))
            .join(Idea, IdeaTag.idea_id == Idea.id)
            .filter(IdeaTag.tag_id == tag_id, Idea.status == IdeaStatus.APPROVED)
            .scalar()
        )

        # Count pending ideas
        pending_ideas = (
            self.db.query(func.count(IdeaTag.id))
            .join(Idea, IdeaTag.idea_id == Idea.id)
            .filter(IdeaTag.tag_id == tag_id, Idea.status == IdeaStatus.PENDING)
            .scalar()
        )

        return {
            "tag": tag,
            "total_ideas": total_ideas or 0,
            "approved_ideas": approved_ideas or 0,
            "pending_ideas": pending_ideas or 0,
        }

    def get_idea_ids_for_tags(
        self, tag_ids: List[int], skip: int = 0, limit: int = 20
    ) -> List[int]:
        """
        Get idea IDs for multiple tags (Phase 3).

        Args:
            tag_ids: List of tag IDs
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of idea IDs (only approved ideas)
        """
        if not tag_ids:
            return []

        return [
            row[0]
            for row in self.db.query(IdeaTag.idea_id)
            .join(Idea, IdeaTag.idea_id == Idea.id)
            .filter(IdeaTag.tag_id.in_(tag_ids), Idea.status == IdeaStatus.APPROVED)
            .group_by(IdeaTag.idea_id)
            .order_by(desc(Idea.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        ]

    def get_tag_idea_count(self, tag_id: int) -> int:
        """
        Get count of approved ideas for a tag (Phase 3).

        Args:
            tag_id: Tag ID

        Returns:
            Number of approved ideas with this tag
        """
        count = (
            self.db.query(func.count(IdeaTag.id))
            .join(Idea, IdeaTag.idea_id == Idea.id)
            .filter(IdeaTag.tag_id == tag_id, Idea.status == IdeaStatus.APPROVED)
            .scalar()
        )
        return count or 0


class IdeaTagRepository(BaseRepository[IdeaTag]):
    """
    Repository for IdeaTag junction table operations.
    """

    def __init__(self, db: Session):
        """
        Initialize IdeaTagRepository.

        Args:
            db: Database session
        """
        super().__init__(IdeaTag, db)

    def add_tag_to_idea(self, idea_id: int, tag_id: int) -> IdeaTag:
        """
        Associate a tag with an idea.

        Args:
            idea_id: Idea ID
            tag_id: Tag ID

        Returns:
            IdeaTag association
        """
        # Check if association already exists
        existing = (
            self.db.query(IdeaTag)
            .filter(IdeaTag.idea_id == idea_id, IdeaTag.tag_id == tag_id)
            .first()
        )

        if existing:
            return existing

        # Create new association
        idea_tag = IdeaTag(idea_id=idea_id, tag_id=tag_id)
        return self.create(idea_tag)

    def remove_tag_from_idea(self, idea_id: int, tag_id: int) -> bool:
        """
        Remove tag association from an idea.

        Args:
            idea_id: Idea ID
            tag_id: Tag ID

        Returns:
            True if removed, False if association didn't exist
        """
        idea_tag = (
            self.db.query(IdeaTag)
            .filter(IdeaTag.idea_id == idea_id, IdeaTag.tag_id == tag_id)
            .first()
        )

        if idea_tag:
            self.delete(idea_tag)
            return True

        return False

    def remove_all_tags_from_idea(self, idea_id: int) -> int:
        """
        Remove all tag associations from an idea.

        Args:
            idea_id: Idea ID

        Returns:
            Number of associations removed
        """
        idea_tags = self.db.query(IdeaTag).filter(IdeaTag.idea_id == idea_id).all()

        count = len(idea_tags)
        for idea_tag in idea_tags:
            self.delete(idea_tag)

        return count

    def get_ideas_by_tag(
        self,
        tag_id: int,
        status_filter: IdeaStatus = IdeaStatus.APPROVED,
        skip: int = 0,
        limit: int = 20,
    ) -> List[int]:
        """
        Get idea IDs for a specific tag.

        Args:
            tag_id: Tag ID
            status_filter: Filter by idea status
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of idea IDs
        """
        query = (
            self.db.query(IdeaTag.idea_id)
            .join(Idea, IdeaTag.idea_id == Idea.id)
            .filter(IdeaTag.tag_id == tag_id, Idea.status == status_filter)
            .order_by(desc(Idea.created_at))
            .offset(skip)
            .limit(limit)
        )

        return [row.idea_id for row in query.all()]
