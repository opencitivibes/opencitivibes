"""
Data Export Service for Law 25 Compliance.

Provides user data portability in JSON and CSV formats.
Article 27 (Right to Access) and Article 28.1 (Right to Portability).
"""

import csv
import io
from datetime import datetime, timezone
from typing import Any, Iterable, Protocol, Union

from sqlalchemy.orm import Session

import repositories.db_models as db_models
from models.exceptions import NotFoundException
from repositories.data_export_repository import DataExportRepository
from repositories.user_repository import UserRepository


class CsvWriterProtocol(Protocol):
    """Protocol for csv.writer objects."""

    def writerow(self, row: Iterable[Any], /) -> Any:
        """Write a row to the CSV output."""
        ...


class DataExportService:
    """Service for exporting user data in compliance with Law 25."""

    @staticmethod
    def _collect_user_data(
        user: db_models.User, user_id: int, export_repo: DataExportRepository
    ) -> dict:
        """Collect all user data via repository and format for export."""
        return {
            "user_profile": DataExportService._format_user_profile(user),
            "ideas": DataExportService._format_ideas(
                export_repo.get_user_ideas_for_export(user_id), export_repo
            ),
            "comments": DataExportService._format_comments(
                export_repo.get_user_comments_for_export(user_id)
            ),
            "votes": DataExportService._format_votes(
                export_repo.get_user_votes_for_export(user_id)
            ),
            "consent_history": DataExportService._format_consent_logs(
                export_repo.get_user_consent_logs(user_id)
            ),
        }

    @staticmethod
    def export_user_data(
        db: Session, user_id: int, export_format: str = "json"
    ) -> Union[dict, str]:
        """Export all user personal data in JSON or CSV format."""
        user = UserRepository(db).get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        user_data = DataExportService._collect_user_data(
            user, user_id, DataExportRepository(db)
        )
        export_data = {
            "export_date": datetime.now(timezone.utc).isoformat(),
            "export_format": export_format,
            **user_data,
        }

        if export_format == "csv":
            return DataExportService._convert_to_csv(export_data)
        return export_data

    @staticmethod
    def _format_user_profile(user: db_models.User) -> dict:
        """Format user profile for export."""
        return {
            "id": user.id,
            "email": str(user.email),
            "username": str(user.username),
            "display_name": str(user.display_name),
            "avatar_url": str(user.avatar_url) if user.avatar_url else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "is_official": bool(user.is_official),
            "official_title": str(user.official_title) if user.official_title else None,
            "trust_score": int(user.trust_score),
            "is_active": bool(user.is_active),
            "consent_terms_accepted": bool(user.consent_terms_accepted),
            "consent_terms_version": user.consent_terms_version,
            "consent_privacy_accepted": bool(user.consent_privacy_accepted),
            "consent_privacy_version": user.consent_privacy_version,
            "consent_timestamp": (
                user.consent_timestamp.isoformat() if user.consent_timestamp else None
            ),
            "marketing_consent": bool(user.marketing_consent),
        }

    @staticmethod
    def _format_ideas(
        ideas: list[db_models.Idea],
        export_repo: DataExportRepository,
    ) -> list[dict]:
        """Format ideas for export with vote counts."""
        if not ideas:
            return []

        # Get vote counts in batch via repository
        idea_ids = [idea.id for idea in ideas]
        vote_counts = export_repo.get_idea_vote_counts(idea_ids)

        return [
            {
                "id": idea.id,
                "title": str(idea.title),
                "description": str(idea.description),
                "status": idea.status.value if idea.status else None,
                "category_id": idea.category_id,
                "category_name": idea.category.name_en if idea.category else None,
                "created_at": idea.created_at.isoformat() if idea.created_at else None,
                "updated_at": (
                    idea.validated_at.isoformat() if idea.validated_at else None
                ),
                "upvote_count": vote_counts.get(idea.id, {}).get("upvotes", 0),
                "downvote_count": vote_counts.get(idea.id, {}).get("downvotes", 0),
                "score": (
                    vote_counts.get(idea.id, {}).get("upvotes", 0)
                    - vote_counts.get(idea.id, {}).get("downvotes", 0)
                ),
                "tags": [tag.name for tag in idea.tags] if idea.tags else [],
            }
            for idea in ideas
        ]

    @staticmethod
    def _format_comments(comments: list[db_models.Comment]) -> list[dict]:
        """Format comments for export."""
        return [
            {
                "id": comment.id,
                "content": str(comment.content),
                "idea_id": comment.idea_id,
                "idea_title": str(comment.idea.title) if comment.idea else None,
                "created_at": (
                    comment.created_at.isoformat() if comment.created_at else None
                ),
                "is_moderated": bool(comment.is_moderated),
            }
            for comment in comments
        ]

    @staticmethod
    def _format_votes(votes: list[db_models.Vote]) -> list[dict]:
        """Format votes for export."""
        return [
            {
                "id": vote.id,
                "idea_id": vote.idea_id,
                "idea_title": str(vote.idea.title) if vote.idea else None,
                "vote_type": vote.vote_type.value if vote.vote_type else None,
                "qualities": (
                    [q.quality.key for q in vote.qualities] if vote.qualities else []
                ),
                "created_at": vote.created_at.isoformat() if vote.created_at else None,
            }
            for vote in votes
        ]

    @staticmethod
    def _format_consent_logs(logs: list[db_models.ConsentLog]) -> list[dict]:
        """Format consent logs for export."""
        return [
            {
                "consent_type": str(log.consent_type),
                "action": str(log.action),
                "policy_version": log.policy_version,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]

    @staticmethod
    def _write_csv_section(
        writer: CsvWriterProtocol,
        title: str,
        data: list[dict],
        empty_message: str,
    ) -> None:
        """Write a section to CSV output using csv.writer object."""
        writer.writerow([f"=== {title} ==="])
        if data:
            headers = list(data[0].keys())
            writer.writerow(headers)
            for item in data:
                writer.writerow([str(item.get(h, "")) for h in headers])
        else:
            writer.writerow([empty_message])
        writer.writerow([])

    @staticmethod
    def _convert_to_csv(data: dict) -> str:
        """
        Convert export data to CSV format.

        Creates multiple sections for different data types.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["=== USER DATA EXPORT ==="])
        writer.writerow(["Export Date", data["export_date"]])
        writer.writerow([])

        # User Profile Section
        writer.writerow(["=== USER PROFILE ==="])
        profile = data["user_profile"]
        for key, value in profile.items():
            writer.writerow([key, value])
        writer.writerow([])

        # Ideas Section
        DataExportService._write_csv_section(
            writer, "IDEAS", data["ideas"], "No ideas found"
        )

        # Comments Section
        DataExportService._write_csv_section(
            writer, "COMMENTS", data["comments"], "No comments found"
        )

        # Votes Section
        DataExportService._write_csv_section(
            writer, "VOTES", data["votes"], "No votes found"
        )

        # Consent History Section
        DataExportService._write_csv_section(
            writer, "CONSENT HISTORY", data["consent_history"], "No consent history"
        )

        return output.getvalue()
