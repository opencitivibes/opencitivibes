"""
Service for admin note operations.
"""

from sqlalchemy.orm import Session

from models.exceptions import (
    AdminNoteNotFoundException,
    InsufficientPermissionsException,
    UserNotFoundException,
)
from repositories.admin_note_repository import AdminNoteRepository
from repositories.db_models import AdminNote


class AdminNoteService:
    """Service for admin note operations."""

    @staticmethod
    def add_note(
        db: Session,
        user_id: int,
        content: str,
        created_by: int,
    ) -> dict:
        """
        Add a note to a user profile.

        Args:
            db: Database session
            user_id: ID of user to add note to
            content: Note content
            created_by: ID of admin creating note

        Returns:
            Created note with author info

        Raises:
            UserNotFoundException: If user not found
        """
        note_repo = AdminNoteRepository(db)

        # Verify user exists
        user = note_repo.get_author(user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found")

        # Get author info
        author = note_repo.get_author(created_by)

        note = AdminNote(
            user_id=user_id,
            content=content,
            created_by=created_by,
        )
        note = note_repo.create_with_refresh(note)

        return {
            "id": note.id,
            "user_id": note.user_id,
            "content": note.content,
            "created_by": note.created_by,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
            "author_username": author.username if author else "Unknown",
            "author_display_name": author.display_name if author else "Unknown",
        }

    @staticmethod
    def get_notes_for_user(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get notes for a user.

        Args:
            db: Database session
            user_id: ID of user
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of notes with author info
        """
        note_repo = AdminNoteRepository(db)
        notes_with_authors = note_repo.get_notes_for_user(user_id, skip, limit)

        return [
            {
                "id": note.id,
                "user_id": note.user_id,
                "content": note.content,
                "created_by": note.created_by,
                "created_at": note.created_at,
                "updated_at": note.updated_at,
                "author_username": username,
                "author_display_name": display_name,
            }
            for note, username, display_name in notes_with_authors
        ]

    @staticmethod
    def update_note(
        db: Session,
        note_id: int,
        content: str,
        updated_by: int,
    ) -> dict:
        """
        Update a note.

        Only the original author can update.

        Args:
            db: Database session
            note_id: ID of note
            content: New content
            updated_by: ID of admin updating

        Returns:
            Updated note

        Raises:
            AdminNoteNotFoundException: If note not found
            InsufficientPermissionsException: If not original author
        """
        note_repo = AdminNoteRepository(db)

        note = note_repo.get_by_id(note_id)
        if not note:
            raise AdminNoteNotFoundException(note_id)

        if int(note.created_by) != updated_by:
            raise InsufficientPermissionsException(
                "Only the original author can edit this note"
            )

        note.content = content  # type: ignore[assignment]
        note_repo.commit()
        note_repo.refresh(note)

        author = note_repo.get_author(int(note.created_by))

        return {
            "id": note.id,
            "user_id": note.user_id,
            "content": note.content,
            "created_by": note.created_by,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
            "author_username": author.username if author else "Unknown",
            "author_display_name": author.display_name if author else "Unknown",
        }

    @staticmethod
    def delete_note(
        db: Session,
        note_id: int,
        deleted_by: int,  # noqa: ARG004
    ) -> None:
        """
        Delete a note.

        Any admin can delete any note.

        Args:
            db: Database session
            note_id: ID of note
            deleted_by: ID of admin deleting (for audit, unused currently)

        Raises:
            AdminNoteNotFoundException: If note not found
        """
        note_repo = AdminNoteRepository(db)

        note = note_repo.get_by_id(note_id)
        if not note:
            raise AdminNoteNotFoundException(note_id)

        note_repo.delete_note(note)
