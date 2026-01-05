"""
Unit tests for AdminNoteService.
"""

import pytest

from models.exceptions import (
    AdminNoteNotFoundException,
    InsufficientPermissionsException,
    UserNotFoundException,
)
from services.admin_note_service import AdminNoteService


class TestAdminNoteServiceAddNote:
    """Tests for AdminNoteService.add_note"""

    def test_add_note_success(self, db_session, test_user, admin_user):
        """Test successfully adding a note to a user."""
        note = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="This user has a history of minor violations.",
            created_by=admin_user.id,
        )

        assert note is not None
        assert note["user_id"] == test_user.id
        assert note["created_by"] == admin_user.id
        assert "history of minor violations" in note["content"]
        assert note["author_username"] == admin_user.username
        assert note["author_display_name"] == admin_user.display_name
        assert note["created_at"] is not None
        assert note["id"] is not None

    def test_add_note_user_not_found(self, db_session, admin_user):
        """Test adding note to non-existent user fails."""
        with pytest.raises(UserNotFoundException):
            AdminNoteService.add_note(
                db=db_session,
                user_id=99999,
                content="Test note",
                created_by=admin_user.id,
            )

    def test_add_note_multiple_notes(self, db_session, test_user, admin_user):
        """Test adding multiple notes to same user."""
        note1 = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="First note",
            created_by=admin_user.id,
        )

        note2 = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Second note",
            created_by=admin_user.id,
        )

        assert note1["id"] != note2["id"]
        assert note1["content"] == "First note"
        assert note2["content"] == "Second note"

    def test_add_note_by_different_admins(
        self, db_session, test_user, admin_user, other_user
    ):
        """Test notes can be added by different admins."""
        note1 = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Note by admin",
            created_by=admin_user.id,
        )

        note2 = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Note by other admin",
            created_by=other_user.id,  # Pretend other_user is also admin
        )

        assert note1["created_by"] == admin_user.id
        assert note2["created_by"] == other_user.id
        assert note1["author_username"] == admin_user.username
        assert note2["author_username"] == other_user.username


class TestAdminNoteServiceGetNotes:
    """Tests for AdminNoteService.get_notes_for_user"""

    def test_get_notes_for_user_empty(self, db_session, test_user):
        """Test getting notes when user has none."""
        notes = AdminNoteService.get_notes_for_user(db_session, test_user.id)

        assert notes == []

    def test_get_notes_for_user(self, db_session, test_user, admin_user):
        """Test getting notes for a user."""
        # Add some notes
        AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="First note",
            created_by=admin_user.id,
        )

        AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Second note",
            created_by=admin_user.id,
        )

        notes = AdminNoteService.get_notes_for_user(db_session, test_user.id)

        assert len(notes) == 2
        # Most recent first
        assert notes[0]["content"] == "Second note"
        assert notes[1]["content"] == "First note"
        assert all("author_username" in note for note in notes)
        assert all("author_display_name" in note for note in notes)

    def test_get_notes_for_user_pagination(self, db_session, test_user, admin_user):
        """Test pagination of notes."""
        # Add multiple notes
        for i in range(5):
            AdminNoteService.add_note(
                db=db_session,
                user_id=test_user.id,
                content=f"Note {i}",
                created_by=admin_user.id,
            )

        # Get first page
        notes = AdminNoteService.get_notes_for_user(
            db_session, test_user.id, skip=0, limit=3
        )
        assert len(notes) == 3

        # Get second page
        notes = AdminNoteService.get_notes_for_user(
            db_session, test_user.id, skip=3, limit=3
        )
        assert len(notes) == 2

    def test_get_notes_for_user_different_users(
        self, db_session, test_user, other_user, admin_user
    ):
        """Test notes are isolated per user."""
        AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Note for test_user",
            created_by=admin_user.id,
        )

        AdminNoteService.add_note(
            db=db_session,
            user_id=other_user.id,
            content="Note for other_user",
            created_by=admin_user.id,
        )

        # Get notes for test_user
        notes = AdminNoteService.get_notes_for_user(db_session, test_user.id)
        assert len(notes) == 1
        assert notes[0]["content"] == "Note for test_user"

        # Get notes for other_user
        notes = AdminNoteService.get_notes_for_user(db_session, other_user.id)
        assert len(notes) == 1
        assert notes[0]["content"] == "Note for other_user"


class TestAdminNoteServiceUpdateNote:
    """Tests for AdminNoteService.update_note"""

    def test_update_note_success(self, db_session, test_user, admin_user):
        """Test successfully updating a note."""
        # Create a note
        note = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Original content",
            created_by=admin_user.id,
        )

        # Update it
        updated = AdminNoteService.update_note(
            db=db_session,
            note_id=note["id"],
            content="Updated content",
            updated_by=admin_user.id,
        )

        assert updated["content"] == "Updated content"
        assert updated["updated_at"] is not None
        assert updated["id"] == note["id"]

    def test_update_note_not_found(self, db_session, admin_user):
        """Test updating non-existent note fails."""
        with pytest.raises(AdminNoteNotFoundException):
            AdminNoteService.update_note(
                db=db_session,
                note_id=99999,
                content="Updated content",
                updated_by=admin_user.id,
            )

    def test_update_note_not_author(
        self, db_session, test_user, admin_user, other_user
    ):
        """Test only original author can update note."""
        # admin_user creates a note
        note = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Original content",
            created_by=admin_user.id,
        )

        # other_user tries to update it
        with pytest.raises(InsufficientPermissionsException):
            AdminNoteService.update_note(
                db=db_session,
                note_id=note["id"],
                content="Trying to update",
                updated_by=other_user.id,
            )

    def test_update_note_author_can_update(self, db_session, test_user, admin_user):
        """Test original author can update their own note."""
        # Create a note
        note = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Original content",
            created_by=admin_user.id,
        )

        # Author updates their own note - should succeed
        updated = AdminNoteService.update_note(
            db=db_session,
            note_id=note["id"],
            content="Updated by author",
            updated_by=admin_user.id,
        )

        assert updated["content"] == "Updated by author"


class TestAdminNoteServiceDeleteNote:
    """Tests for AdminNoteService.delete_note"""

    def test_delete_note_success(self, db_session, test_user, admin_user):
        """Test successfully deleting a note."""
        # Create a note
        note = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Note to delete",
            created_by=admin_user.id,
        )

        # Delete it
        AdminNoteService.delete_note(
            db=db_session,
            note_id=note["id"],
            deleted_by=admin_user.id,
        )

        # Verify it's deleted
        notes = AdminNoteService.get_notes_for_user(db_session, test_user.id)
        assert len(notes) == 0

        # Also verify via direct query
        from repositories.admin_note_repository import AdminNoteRepository

        repo = AdminNoteRepository(db_session)
        deleted_note = repo.get_by_id(note["id"])
        assert deleted_note is None

    def test_delete_note_not_found(self, db_session, admin_user):
        """Test deleting non-existent note fails."""
        with pytest.raises(AdminNoteNotFoundException):
            AdminNoteService.delete_note(
                db=db_session,
                note_id=99999,
                deleted_by=admin_user.id,
            )

    def test_delete_note_any_admin_can_delete(
        self, db_session, test_user, admin_user, other_user
    ):
        """Test any admin can delete any note."""
        # admin_user creates a note
        note = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Note to delete",
            created_by=admin_user.id,
        )

        # other_user (different admin) deletes it - should succeed
        AdminNoteService.delete_note(
            db=db_session,
            note_id=note["id"],
            deleted_by=other_user.id,
        )

        # Verify it's deleted
        notes = AdminNoteService.get_notes_for_user(db_session, test_user.id)
        assert len(notes) == 0

    def test_delete_note_cascade_on_user(self, db_session, test_user, admin_user):
        """Test notes are maintained even if referenced properly."""
        # Create a note
        AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Note about user",
            created_by=admin_user.id,
        )

        # Note should exist
        notes = AdminNoteService.get_notes_for_user(db_session, test_user.id)
        assert len(notes) == 1


class TestAdminNoteServiceComprehensive:
    """Comprehensive tests combining multiple operations."""

    def test_full_note_lifecycle(self, db_session, test_user, admin_user):
        """Test complete note lifecycle: create, read, update, delete."""
        # Create
        note = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Initial note",
            created_by=admin_user.id,
        )
        assert note["content"] == "Initial note"

        # Read
        notes = AdminNoteService.get_notes_for_user(db_session, test_user.id)
        assert len(notes) == 1
        assert notes[0]["id"] == note["id"]

        # Update
        updated = AdminNoteService.update_note(
            db=db_session,
            note_id=note["id"],
            content="Updated note",
            updated_by=admin_user.id,
        )
        assert updated["content"] == "Updated note"

        # Verify update persisted
        notes = AdminNoteService.get_notes_for_user(db_session, test_user.id)
        assert notes[0]["content"] == "Updated note"

        # Delete
        AdminNoteService.delete_note(
            db=db_session,
            note_id=note["id"],
            deleted_by=admin_user.id,
        )

        # Verify deletion
        notes = AdminNoteService.get_notes_for_user(db_session, test_user.id)
        assert len(notes) == 0

    def test_multiple_admins_collaboration(
        self, db_session, test_user, admin_user, other_user
    ):
        """Test multiple admins can collaborate on notes."""
        # admin_user adds first note
        note1 = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="First warning by admin1",
            created_by=admin_user.id,
        )

        # other_user adds second note
        note2 = AdminNoteService.add_note(
            db=db_session,
            user_id=test_user.id,
            content="Follow-up by admin2",
            created_by=other_user.id,
        )

        # Get all notes
        notes = AdminNoteService.get_notes_for_user(db_session, test_user.id)
        assert len(notes) == 2

        # Verify authors
        note_authors = {note["created_by"] for note in notes}
        assert admin_user.id in note_authors
        assert other_user.id in note_authors

        # other_user can delete admin_user's note
        AdminNoteService.delete_note(
            db=db_session,
            note_id=note1["id"],
            deleted_by=other_user.id,
        )

        # Only one note remains
        notes = AdminNoteService.get_notes_for_user(db_session, test_user.id)
        assert len(notes) == 1
        assert notes[0]["id"] == note2["id"]
