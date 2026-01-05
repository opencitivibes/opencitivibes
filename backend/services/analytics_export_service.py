"""
Analytics Export Service - CSV generation for data export.

Handles conversion of analytics data to CSV format.
Follows the service pattern used throughout the codebase.
"""

import csv
from datetime import datetime
from io import StringIO
from typing import Optional

from sqlalchemy.orm import Session

from models.exceptions import ValidationException
from services.analytics_service import AnalyticsService


class AnalyticsExportService:
    """Service for exporting analytics data as CSV."""

    @staticmethod
    def generate_csv(
        db: Session,
        data_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> str:
        """
        Generate CSV content for the specified data type.

        Args:
            db: Database session
            data_type: Type of data (overview, ideas, users, categories)
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            CSV content as string.

        Raises:
            ValidationException: If data_type is invalid.
        """
        if data_type == "overview":
            return AnalyticsExportService._export_overview(db)
        elif data_type == "ideas":
            return AnalyticsExportService._export_ideas(db, start_date, end_date)
        elif data_type == "users":
            return AnalyticsExportService._export_users(db, start_date, end_date)
        elif data_type == "categories":
            return AnalyticsExportService._export_categories(db)
        else:
            raise ValidationException(f"Invalid data type: {data_type}")

    @staticmethod
    def _export_overview(db: Session) -> str:
        """Export overview metrics as CSV."""
        overview = AnalyticsService.get_overview(db)

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Metric", "Value"])

        # Data
        writer.writerow(["Total Users", overview.total_users])
        writer.writerow(["Active Users", overview.active_users])
        writer.writerow(["Total Ideas", overview.total_ideas])
        writer.writerow(["Approved Ideas", overview.approved_ideas])
        writer.writerow(["Pending Ideas", overview.pending_ideas])
        writer.writerow(["Rejected Ideas", overview.rejected_ideas])
        writer.writerow(["Total Votes", overview.total_votes])
        writer.writerow(["Total Comments", overview.total_comments])
        writer.writerow(["Ideas This Week", overview.ideas_this_week])
        writer.writerow(["Votes This Week", overview.votes_this_week])
        writer.writerow(["Comments This Week", overview.comments_this_week])
        writer.writerow(["Users This Week", overview.users_this_week])
        writer.writerow(["Generated At", overview.generated_at.isoformat()])

        return output.getvalue()

    @staticmethod
    def _export_ideas(
        db: Session,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> str:
        """Export ideas list as CSV with vote and comment counts."""
        from repositories.analytics_repository import AnalyticsRepository

        ideas = AnalyticsRepository.get_ideas_for_export(db, start_date, end_date)

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "ID",
                "Title",
                "Category",
                "Status",
                "Author",
                "Upvotes",
                "Downvotes",
                "Score",
                "Comments",
                "Created At",
                "Validated At",
            ]
        )

        # Data - now all in single row from query, no additional queries needed
        for idea in ideas:
            upvotes = int(idea.upvotes)
            downvotes = int(idea.downvotes)
            score = upvotes - downvotes
            status_value = (
                idea.status.value if hasattr(idea.status, "value") else idea.status
            )

            writer.writerow(
                [
                    idea.id,
                    idea.title,
                    idea.category,
                    status_value,
                    idea.author,
                    upvotes,
                    downvotes,
                    score,
                    int(idea.comment_count),
                    idea.created_at.isoformat() if idea.created_at else "",
                    idea.validated_at.isoformat() if idea.validated_at else "",
                ]
            )

        return output.getvalue()

    @staticmethod
    def _export_users(
        db: Session,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> str:
        """Export users list as CSV with contribution counts."""
        from repositories.analytics_repository import AnalyticsRepository

        users = AnalyticsRepository.get_users_for_export(db, start_date, end_date)

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "ID",
                "Username",
                "Display Name",
                "Email",
                "Active",
                "Admin",
                "Ideas Count",
                "Votes Cast",
                "Comments",
                "Created At",
            ]
        )

        # Data - now all in single row from query, no additional queries needed
        for user in users:
            writer.writerow(
                [
                    user.id,
                    user.username,
                    user.display_name or "",
                    user.email,
                    "Yes" if user.is_active else "No",
                    "Yes" if user.is_global_admin else "No",
                    int(user.ideas_count),
                    int(user.votes_count),
                    int(user.comments_count),
                    user.created_at.isoformat() if user.created_at else "",
                ]
            )

        return output.getvalue()

    @staticmethod
    def _export_categories(db: Session) -> str:
        """Export category analytics as CSV."""
        categories = AnalyticsService.get_categories_analytics(db)

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "ID",
                "Name (EN)",
                "Name (FR)",
                "Total Ideas",
                "Approved",
                "Pending",
                "Rejected",
                "Total Votes",
                "Total Comments",
                "Avg Score",
                "Approval Rate",
            ]
        )

        # Data
        for cat in categories.categories:
            writer.writerow(
                [
                    cat.id,
                    cat.name_en,
                    cat.name_fr,
                    cat.total_ideas,
                    cat.approved_ideas,
                    cat.pending_ideas,
                    cat.rejected_ideas,
                    cat.total_votes,
                    cat.total_comments,
                    f"{cat.avg_score:.2f}",
                    f"{cat.approval_rate * 100:.1f}%",
                ]
            )

        return output.getvalue()
