"""
Privacy Incident Management Service for Law 25 Compliance.

Manages privacy incidents including breach registration and notification.
Required by Articles 3.5, 3.6, and 3.7 of Law 25.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

import models.schemas as schemas
from models.config import settings
from repositories import db_models
from repositories.incident_repository import IncidentRepository


class IncidentService:
    """Service for managing privacy incidents per Law 25 requirements."""

    @staticmethod
    def _generate_incident_number(repo: IncidentRepository, now: datetime) -> str:
        """Generate unique incident number (INC-YYYY-NNN)."""
        year = now.year
        count = repo.count_by_year(year) + 1
        return f"INC-{year}-{count:03d}"

    @staticmethod
    def _determine_notifications(
        severity: str, affected_users: Optional[list[int]]
    ) -> tuple[bool, bool]:
        """Determine notification requirements per Law 25 Article 3.6."""
        cai_required = severity in ["high", "critical"]
        users_required = cai_required and bool(affected_users)
        return cai_required, users_required

    @staticmethod
    def _build_incident(
        incident_number: str,
        incident_type: str,
        severity: str,
        title: str,
        description: str,
        discovered_at: datetime,
        occurred_at: Optional[datetime],
        affected_users: Optional[list[int]],
        data_types: Optional[list[str]],
        reported_by: Optional[int],
        cai_required: bool,
        users_required: bool,
    ) -> db_models.PrivacyIncident:
        """Build PrivacyIncident model instance."""
        return db_models.PrivacyIncident(
            incident_number=incident_number,
            incident_type=incident_type,
            severity=severity,
            status="open",
            title=title,
            description=description,
            discovered_at=discovered_at,
            occurred_at=occurred_at,
            affected_users_count=len(affected_users) if affected_users else 0,
            affected_user_ids=json.dumps(affected_users) if affected_users else None,
            data_types_involved=json.dumps(data_types) if data_types else None,
            risk_of_harm="serious" if severity in ["high", "critical"] else "medium",
            cai_notification_required=cai_required,
            users_notification_required=users_required,
            reported_by_user_id=reported_by,
        )

    @staticmethod
    def create_incident(
        db: Session,
        incident_type: str,
        severity: str,
        title: str,
        description: str,
        discovered_at: Optional[datetime] = None,
        occurred_at: Optional[datetime] = None,
        affected_users: Optional[list[int]] = None,
        data_types: Optional[list[str]] = None,
        reported_by: Optional[int] = None,
    ) -> db_models.PrivacyIncident:
        """Create a new privacy incident."""
        now = datetime.now(timezone.utc)
        repo = IncidentRepository(db)

        incident_number = IncidentService._generate_incident_number(repo, now)
        cai_required, users_required = IncidentService._determine_notifications(
            severity, affected_users
        )

        incident = IncidentService._build_incident(
            incident_number=incident_number,
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
            discovered_at=discovered_at or now,
            occurred_at=occurred_at,
            affected_users=affected_users,
            data_types=data_types,
            reported_by=reported_by,
            cai_required=cai_required,
            users_required=users_required,
        )

        created = repo.create(incident)
        IncidentService._log_incident_created(created)
        return created

    @staticmethod
    def _log_incident_created(incident: db_models.PrivacyIncident) -> None:
        """Log incident creation."""
        logger.warning(
            f"Privacy incident created: {incident.incident_number}",
            extra={
                "incident_number": incident.incident_number,
                "incident_type": incident.incident_type,
                "severity": incident.severity,
                "affected_users_count": incident.affected_users_count,
            },
        )

    @staticmethod
    def create_incident_response(
        db: Session,
        incident_type: str,
        severity: str,
        title: str,
        description: str,
        discovered_at: Optional[datetime] = None,
        occurred_at: Optional[datetime] = None,
        affected_users: Optional[list[int]] = None,
        data_types: Optional[list[str]] = None,
        reported_by: Optional[int] = None,
    ) -> schemas.IncidentCreateResponse:
        """Create a new privacy incident and return schema response."""
        incident = IncidentService.create_incident(
            db=db,
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
            discovered_at=discovered_at,
            occurred_at=occurred_at,
            affected_users=affected_users,
            data_types=data_types,
            reported_by=reported_by,
        )
        return schemas.IncidentCreateResponse(
            incident_number=incident.incident_number,
            id=incident.id,
        )

    @staticmethod
    def update_incident_status(
        db: Session,
        incident_id: int,
        status: str,
        notes: Optional[str] = None,
    ) -> db_models.PrivacyIncident:
        """
        Update incident status.

        Args:
            db: Database session
            incident_id: ID of the incident
            status: New status (open, investigating, contained, mitigated, closed)
            notes: Optional notes about the status change

        Returns:
            Updated PrivacyIncident record

        Raises:
            ValueError: If incident not found
        """
        repo = IncidentRepository(db)
        incident = repo.get_by_id(incident_id)

        if not incident:
            raise ValueError("Incident not found")

        now = datetime.now(timezone.utc)

        incident.status = status
        if status == "contained":
            incident.contained_at = now
        elif status == "closed":
            incident.resolved_at = now

        if notes:
            existing = incident.mitigation_measures or ""
            incident.mitigation_measures = (
                f"{existing}\n\n[{now.isoformat()}] {notes}".strip()
            )

        updated = repo.update(incident)

        logger.info(
            f"Incident {incident.incident_number} status updated to {status}",
            extra={"incident_id": incident_id, "new_status": status},
        )

        return updated

    @staticmethod
    def update_incident_status_response(
        db: Session,
        incident_id: int,
        status: str,
        notes: Optional[str] = None,
    ) -> schemas.IncidentStatusUpdateResponse:
        """Update incident status and return schema response."""
        incident = IncidentService.update_incident_status(
            db=db,
            incident_id=incident_id,
            status=status,
            notes=notes,
        )
        return schemas.IncidentStatusUpdateResponse(
            incident_number=incident.incident_number,
            status=incident.status,
        )

    @staticmethod
    def record_cai_notification(
        db: Session,
        incident_id: int,
        reference_number: Optional[str] = None,
    ) -> db_models.PrivacyIncident:
        """
        Record that CAI (Commission d'accès à l'information) has been notified.

        Args:
            db: Database session
            incident_id: ID of the incident
            reference_number: CAI reference number if provided

        Returns:
            Updated PrivacyIncident record

        Raises:
            ValueError: If incident not found
        """
        repo = IncidentRepository(db)
        incident = repo.get_by_id(incident_id)

        if not incident:
            raise ValueError("Incident not found")

        incident.cai_notified = True
        incident.cai_notified_at = datetime.now(timezone.utc)
        incident.cai_reference_number = reference_number

        updated = repo.update(incident)

        logger.info(
            f"CAI notified for incident {incident.incident_number}",
            extra={"reference_number": reference_number},
        )

        return updated

    @staticmethod
    def record_cai_notification_response(
        db: Session,
        incident_id: int,
        reference_number: Optional[str] = None,
    ) -> schemas.CAINotificationResponse:
        """Record CAI notification and return schema response."""
        incident = IncidentService.record_cai_notification(
            db=db,
            incident_id=incident_id,
            reference_number=reference_number,
        )
        return schemas.CAINotificationResponse(
            incident_number=incident.incident_number,
            cai_notified=incident.cai_notified,
            cai_notified_at=incident.cai_notified_at,
        )

    @staticmethod
    def record_user_notifications(
        db: Session,
        incident_id: int,
    ) -> db_models.PrivacyIncident:
        """
        Record that affected users have been notified.

        Args:
            db: Database session
            incident_id: ID of the incident

        Returns:
            Updated PrivacyIncident record

        Raises:
            ValueError: If incident not found
        """
        repo = IncidentRepository(db)
        incident = repo.get_by_id(incident_id)

        if not incident:
            raise ValueError("Incident not found")

        incident.users_notified = True
        incident.users_notified_at = datetime.now(timezone.utc)

        updated = repo.update(incident)

        logger.info(f"Users notified for incident {incident.incident_number}")

        return updated

    @staticmethod
    def record_user_notifications_response(
        db: Session,
        incident_id: int,
    ) -> schemas.UserNotificationResponse:
        """Record user notifications and return schema response."""
        incident = IncidentService.record_user_notifications(
            db=db,
            incident_id=incident_id,
        )
        return schemas.UserNotificationResponse(
            incident_number=incident.incident_number,
            users_notified=incident.users_notified,
            users_notified_at=incident.users_notified_at,
        )

    @staticmethod
    def get_incidents_requiring_notification(db: Session) -> dict:
        """
        Get incidents that still need notifications.

        Returns:
            Dictionary with 'cai_pending' and 'users_pending' lists
        """
        repo = IncidentRepository(db)
        cai_pending = repo.get_requiring_cai_notification()
        users_pending = repo.get_requiring_user_notification()

        return {
            "cai_pending": [i.incident_number for i in cai_pending],
            "users_pending": [i.incident_number for i in users_pending],
        }

    @staticmethod
    def get_incident_by_id(
        db: Session, incident_id: int
    ) -> Optional[db_models.PrivacyIncident]:
        """Get incident by ID."""
        repo = IncidentRepository(db)
        return repo.get_by_id(incident_id)

    @staticmethod
    def get_incident_by_number(
        db: Session, incident_number: str
    ) -> Optional[db_models.PrivacyIncident]:
        """Get incident by incident number."""
        repo = IncidentRepository(db)
        return repo.get_by_number(incident_number)

    @staticmethod
    def _incident_to_detail_schema(
        incident: db_models.PrivacyIncident,
    ) -> schemas.IncidentDetail:
        """Convert incident model to IncidentDetail schema."""
        data_types = None
        if incident.data_types_involved:
            data_types = json.loads(incident.data_types_involved)

        return schemas.IncidentDetail(
            id=incident.id,
            incident_number=incident.incident_number,
            incident_type=incident.incident_type,
            severity=incident.severity,
            status=incident.status,
            title=incident.title,
            description=incident.description,
            root_cause=incident.root_cause,
            discovered_at=incident.discovered_at,
            occurred_at=incident.occurred_at,
            contained_at=incident.contained_at,
            resolved_at=incident.resolved_at,
            affected_users_count=incident.affected_users_count,
            data_types_involved=data_types,
            risk_of_harm=incident.risk_of_harm,
            cai_notification_required=incident.cai_notification_required,
            cai_notified=incident.cai_notified,
            cai_notified_at=incident.cai_notified_at,
            cai_reference_number=incident.cai_reference_number,
            users_notification_required=incident.users_notification_required,
            users_notified=incident.users_notified,
            users_notified_at=incident.users_notified_at,
            mitigation_measures=incident.mitigation_measures,
            preventive_measures=incident.preventive_measures,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
        )

    @staticmethod
    def get_incident_detail(
        db: Session,
        incident_id: int,
    ) -> Optional[schemas.IncidentDetail]:
        """Get full details of a privacy incident as schema."""
        repo = IncidentRepository(db)
        incident = repo.get_by_id(incident_id)
        if not incident:
            return None
        return IncidentService._incident_to_detail_schema(incident)

    @staticmethod
    def _incident_to_summary(
        incident: db_models.PrivacyIncident,
    ) -> schemas.IncidentSummary:
        """Convert incident model to IncidentSummary schema."""
        return schemas.IncidentSummary(
            id=incident.id,
            incident_number=incident.incident_number,
            incident_type=incident.incident_type,
            severity=incident.severity,
            status=incident.status,
            title=incident.title,
            affected_users_count=incident.affected_users_count,
            cai_notified=incident.cai_notified,
            users_notified=incident.users_notified,
            discovered_at=incident.discovered_at,
        )

    @staticmethod
    def list_incidents_response(
        db: Session,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> schemas.IncidentListResponse:
        """List incidents with optional filters, returning schema response."""
        repo = IncidentRepository(db)
        incidents = repo.list_incidents(
            status=status, severity=severity, limit=limit, offset=offset
        )
        total = repo.count_incidents(status=status, severity=severity)
        items = [IncidentService._incident_to_summary(i) for i in incidents]
        return schemas.IncidentListResponse(
            items=items, total=total, skip=offset, limit=limit
        )

    @staticmethod
    def _format_incident_date(
        incident: db_models.PrivacyIncident, language: str
    ) -> str:
        """Format incident date for notification."""
        incident_date = incident.occurred_at or incident.discovered_at
        if language == "fr":
            return incident_date.strftime("%d %B %Y")
        return incident_date.strftime("%B %d, %Y")

    @staticmethod
    def _parse_data_types(incident: db_models.PrivacyIncident) -> list[str]:
        """Parse data types from JSON."""
        if incident.data_types_involved:
            return json.loads(incident.data_types_involved)
        return []

    @staticmethod
    def generate_cai_notification_content(
        incident: db_models.PrivacyIncident,
    ) -> dict:
        """
        Generate content for CAI notification per Law 25 Article 3.7.

        Required content:
        - Description of incident
        - Date or period of incident
        - Description of personal information involved
        - Measures taken to mitigate harm
        - Contact information for questions

        Args:
            incident: PrivacyIncident record

        Returns:
            Dictionary with required notification fields
        """
        return {
            "incident_number": incident.incident_number,
            "organization": settings.PROJECT_NAME,
            "contact_email": settings.PRIVACY_OFFICER_EMAIL,
            "contact_name": settings.PRIVACY_OFFICER_NAME,
            "incident_description": incident.description,
            "incident_date": (
                incident.occurred_at or incident.discovered_at
            ).isoformat(),
            "discovery_date": incident.discovered_at.isoformat(),
            "personal_information_involved": IncidentService._parse_data_types(
                incident
            ),
            "number_of_individuals_affected": incident.affected_users_count,
            "risk_of_serious_injury": incident.risk_of_harm == "serious",
            "mitigation_measures": incident.mitigation_measures
            or "Under investigation",
            "preventive_measures": incident.preventive_measures or "To be determined",
        }

    @staticmethod
    def generate_user_notification_content(
        incident: db_models.PrivacyIncident,
        user: db_models.User,
        language: str = "fr",
    ) -> dict:
        """
        Generate content for user notification per Law 25 Article 3.7.

        Args:
            incident: PrivacyIncident record
            user: User to notify
            language: Language code ('fr' or 'en')

        Returns:
            Dictionary with notification content in specified language
        """
        data_types = IncidentService._parse_data_types(incident)
        data_types_str = ", ".join(data_types) if data_types else None
        date_str = IncidentService._format_incident_date(incident, language)
        mitigation = incident.mitigation_measures

        if language == "fr":
            return IncidentService._get_notification_template_fr(
                incident, user, date_str, data_types_str, mitigation
            )
        return IncidentService._get_notification_template_en(
            incident, user, date_str, data_types_str, mitigation
        )

    @staticmethod
    def _get_notification_template_fr(
        incident: db_models.PrivacyIncident,
        user: db_models.User,
        date_str: str,
        data_types_str: Optional[str],
        mitigation: Optional[str],
    ) -> dict:
        """Get French notification template."""
        return {
            "subject": (
                f"Avis important concernant vos données personnelles - "
                f"{incident.incident_number}"
            ),
            "greeting": f"Bonjour {user.display_name},",
            "body": (
                "Nous vous informons d'un incident de confidentialité qui "
                "pourrait avoir affecté vos données personnelles.\n\n"
                f"**Description de l'incident:**\n{incident.description}\n\n"
                f"**Date de l'incident:**\n{date_str}\n\n"
                f"**Données potentiellement concernées:**\n"
                f"{data_types_str or 'À déterminer'}\n\n"
                f"**Mesures prises:**\n{mitigation or 'Enquête en cours'}\n\n"
                "**Ce que vous pouvez faire:**\n"
                "- Changez votre mot de passe par précaution\n"
                "- Surveillez toute activité suspecte sur votre compte\n"
                "- Contactez-nous si vous avez des questions\n\n"
                f"**Contact:**\n{settings.PRIVACY_OFFICER_EMAIL}\n\n"
                "Nous vous prions d'accepter nos excuses pour cet incident.\n\n"
                f"L'équipe {settings.PROJECT_NAME}"
            ),
        }

    @staticmethod
    def _get_notification_template_en(
        incident: db_models.PrivacyIncident,
        user: db_models.User,
        date_str: str,
        data_types_str: Optional[str],
        mitigation: Optional[str],
    ) -> dict:
        """Get English notification template."""
        return {
            "subject": (
                f"Important notice regarding your personal data - "
                f"{incident.incident_number}"
            ),
            "greeting": f"Hello {user.display_name},",
            "body": (
                "We are informing you of a privacy incident that may have "
                "affected your personal data.\n\n"
                f"**Incident Description:**\n{incident.description}\n\n"
                f"**Date of Incident:**\n{date_str}\n\n"
                f"**Data Potentially Affected:**\n"
                f"{data_types_str or 'To be determined'}\n\n"
                f"**Measures Taken:**\n"
                f"{mitigation or 'Investigation in progress'}\n\n"
                "**What You Can Do:**\n"
                "- Change your password as a precaution\n"
                "- Monitor your account for any suspicious activity\n"
                "- Contact us if you have any questions\n\n"
                f"**Contact:**\n{settings.PRIVACY_OFFICER_EMAIL}\n\n"
                "We sincerely apologize for this incident.\n\n"
                f"The {settings.PROJECT_NAME} Team"
            ),
        }
