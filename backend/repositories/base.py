"""
Base repository class providing common database operations.
"""

from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from repositories.database import Base

T = TypeVar("T", bound=Base)  # type: ignore[type-arg]


class BaseRepository(Generic[T]):
    """
    Base repository providing common CRUD operations.

    Type parameter T should be a SQLAlchemy model class.
    """

    def __init__(self, model: type[T], db: Session):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def get_by_id(self, id: int) -> T | None:
        """
        Get entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """
        Get all entities with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of entities
        """
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def add(self, entity: T) -> None:
        """
        Add entity to session without committing.

        Use this when you need to add multiple entities before a single commit.

        Args:
            entity: Entity to add
        """
        self.db.add(entity)

    def create(self, entity: T) -> T:
        """
        Create new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity
        """
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: T) -> T:
        """
        Update existing entity.

        Args:
            entity: Entity to update

        Returns:
            Updated entity
        """
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: T) -> None:
        """
        Delete entity.

        Args:
            entity: Entity to delete
        """
        self.db.delete(entity)
        self.db.commit()

    def count(self) -> int:
        """
        Count total number of entities.

        Returns:
            Total count
        """
        return self.db.query(self.model).count()

    def commit(self) -> None:
        """Commit the current transaction."""
        self.db.commit()

    def flush(self) -> None:
        """Flush pending changes without committing."""
        self.db.flush()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.db.rollback()

    def refresh(self, entity: T) -> None:
        """
        Refresh entity from database.

        Args:
            entity: Entity to refresh
        """
        self.db.refresh(entity)

    def add_all(self, entities: list[T]) -> None:
        """
        Add multiple entities to session without committing.

        Use this when you need to add multiple entities before a single commit.

        Args:
            entities: List of entities to add
        """
        self.db.add_all(entities)
