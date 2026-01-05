"""
Category repository for database operations.
"""

from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, case
import repositories.db_models as db_models
from .base import BaseRepository


class CategoryRepository(BaseRepository[db_models.Category]):
    """Repository for Category entity database operations."""

    def __init__(self, db: Session):
        """
        Initialize category repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.Category, db)

    def get_all_with_statistics(self) -> List[Dict]:
        """
        Get all categories with statistics (optimized single query).

        This method fixes the N+1 query problem by using a single query
        with GROUP BY and conditional aggregation.

        Returns:
            List of dictionaries with category statistics
        """
        # Single query with aggregation to avoid N+1 problem
        query = (
            self.db.query(
                db_models.Category.id.label("category_id"),
                db_models.Category.name_en.label("category_name_en"),
                db_models.Category.name_fr.label("category_name_fr"),
                func.count(db_models.Idea.id).label("total_ideas"),
                func.sum(
                    case(
                        (db_models.Idea.status == db_models.IdeaStatus.APPROVED, 1),
                        else_=0,
                    )
                ).label("approved_ideas"),
                func.sum(
                    case(
                        (db_models.Idea.status == db_models.IdeaStatus.PENDING, 1),
                        else_=0,
                    )
                ).label("pending_ideas"),
                func.sum(
                    case(
                        (db_models.Idea.status == db_models.IdeaStatus.REJECTED, 1),
                        else_=0,
                    )
                ).label("rejected_ideas"),
            )
            .outerjoin(
                db_models.Idea, db_models.Category.id == db_models.Idea.category_id
            )
            .group_by(
                db_models.Category.id,
                db_models.Category.name_en,
                db_models.Category.name_fr,
            )
            .all()
        )

        # Convert to list of dictionaries
        result = []
        for row in query:
            result.append(
                {
                    "category_id": row.category_id,
                    "category_name_en": row.category_name_en,
                    "category_name_fr": row.category_name_fr,
                    "total_ideas": row.total_ideas or 0,
                    "approved_ideas": row.approved_ideas or 0,
                    "pending_ideas": row.pending_ideas or 0,
                    "rejected_ideas": row.rejected_ideas or 0,
                }
            )

        return result

    def get_by_name(
        self, name_en: str | None = None, name_fr: str | None = None
    ) -> db_models.Category | None:
        """
        Get category by English or French name.

        Args:
            name_en: English name
            name_fr: French name

        Returns:
            Category if found, None otherwise
        """
        if name_en:
            return (
                self.db.query(db_models.Category)
                .filter(db_models.Category.name_en == name_en)
                .first()
            )
        elif name_fr:
            return (
                self.db.query(db_models.Category)
                .filter(db_models.Category.name_fr == name_fr)
                .first()
            )
        return None
