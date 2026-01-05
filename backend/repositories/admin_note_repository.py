"""
Repository for admin note operations.
"""

from typing import Any

from sqlalchemy.orm import Session

from repositories.base import BaseRepository
from repositories.db_models import AdminNote, User


class AdminNoteRepository(BaseRepository[AdminNote]):
    """Repository for admin note data access."""

    def __init__(self, db: Session):
        """
        Initialize admin note repository.

        Args:
            db: Database session
        """
        super().__init__(AdminNote, db)

    def get_notes_for_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Any]:
        """
        Get notes for a user with author info.

        Args:
            user_id: ID of user
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of (note, author_username, author_display_name)
        """
        return (
            self.db.query(AdminNote, User.username, User.display_name)
            .join(User, AdminNote.created_by == User.id)
            .filter(AdminNote.user_id == user_id)
            .order_by(AdminNote.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_notes_for_user(self, user_id: int) -> int:
        """
        Get count of notes for a user.

        Args:
            user_id: ID of user

        Returns:
            Number of notes for the user
        """
        return self.db.query(AdminNote).filter(AdminNote.user_id == user_id).count()

    def get_author(self, user_id: int) -> User | None:
        """
        Get author user by ID.

        Args:
            user_id: ID of user

        Returns:
            User if found, None otherwise
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def create_with_refresh(self, note: AdminNote) -> AdminNote:
        """
        Create a note and refresh from database.

        Args:
            note: AdminNote to create

        Returns:
            Created and refreshed note
        """
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def delete_note(self, note: AdminNote) -> None:
        """
        Delete a note.

        Args:
            note: AdminNote to delete
        """
        self.db.delete(note)
        self.db.commit()
