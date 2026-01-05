"""Tests for DataExportService."""

from sqlalchemy.orm import Session

from repositories.db_models import Comment, Idea, User, Vote
from services.data_export_service import DataExportService


class TestDataExportService:
    """Tests for user data export functionality."""

    def test_export_user_data_json_format(
        self, db_session: Session, test_user: User
    ) -> None:
        """Test exporting user data in JSON format."""
        result = DataExportService.export_user_data(
            db_session, test_user.id, export_format="json"
        )

        assert isinstance(result, dict)
        assert "user_profile" in result
        assert "ideas" in result
        assert "comments" in result
        assert "votes" in result
        assert "consent_history" in result
        assert "export_date" in result

    def test_export_user_data_csv_format(
        self, db_session: Session, test_user: User
    ) -> None:
        """Test exporting user data in CSV format."""
        result = DataExportService.export_user_data(
            db_session, test_user.id, export_format="csv"
        )

        assert isinstance(result, str)
        assert "=== USER DATA EXPORT ===" in result
        assert "=== USER PROFILE ===" in result
        assert "=== IDEAS ===" in result
        assert "=== COMMENTS ===" in result
        assert "=== VOTES ===" in result

    def test_export_user_data_includes_profile(
        self, db_session: Session, test_user: User
    ) -> None:
        """Test that profile data is included correctly."""
        result = DataExportService.export_user_data(
            db_session, test_user.id, export_format="json"
        )

        assert isinstance(result, dict)
        profile = result["user_profile"]
        assert profile["email"] == test_user.email
        assert profile["username"] == test_user.username

    def test_export_user_data_includes_ideas(
        self, db_session: Session, test_user: User, test_idea: Idea
    ) -> None:
        """Test that user's ideas are included."""
        result = DataExportService.export_user_data(
            db_session, test_user.id, export_format="json"
        )

        assert isinstance(result, dict)
        assert len(result["ideas"]) >= 1
        idea_titles = [idea["title"] for idea in result["ideas"]]
        assert test_idea.title in idea_titles

    def test_export_user_data_includes_comments(
        self, db_session: Session, test_user: User, test_comment: Comment
    ) -> None:
        """Test that user's comments are included."""
        result = DataExportService.export_user_data(
            db_session, test_user.id, export_format="json"
        )

        assert isinstance(result, dict)
        assert len(result["comments"]) >= 1
        comment_contents = [c["content"] for c in result["comments"]]
        assert test_comment.content in comment_contents

    def test_export_user_data_includes_votes(
        self, db_session: Session, test_user: User, test_vote: Vote
    ) -> None:
        """Test that user's votes are included."""
        result = DataExportService.export_user_data(
            db_session, test_user.id, export_format="json"
        )

        assert isinstance(result, dict)
        assert len(result["votes"]) >= 1

    def test_export_user_data_invalid_format(
        self, db_session: Session, test_user: User
    ) -> None:
        """Test that invalid format defaults to JSON."""
        result = DataExportService.export_user_data(
            db_session, test_user.id, export_format="xml"
        )

        assert isinstance(result, dict)
