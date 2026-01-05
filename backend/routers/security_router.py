"""
Security and Incident Management Router for Law 25 Compliance.

Provides admin endpoints for:
- Security audit log viewing
- Security alert monitoring
- Privacy incident management
- CAI/user notification tracking
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from helpers.pagination import PaginationLimitLarge, PaginationSkip
from models.exceptions import NotFoundException
from repositories.database import get_db
from services.incident_service import IncidentService
from services.security_audit_service import SecurityAuditService

router = APIRouter(prefix="/admin/security", tags=["security"])


# ============================================================================
# Security Audit Log Endpoints
# ============================================================================


@router.get("/audit-logs", response_model=list[schemas.SecurityAuditLogResponse])
def get_security_audit_logs(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    skip: PaginationSkip = 0,
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> list[schemas.SecurityAuditLogResponse]:
    """
    Get security audit logs (admin only).

    Retrieve audit logs for security monitoring and investigation.
    """
    return SecurityAuditService.get_audit_logs_response(
        db=db,
        event_type=event_type,
        user_id=user_id,
        severity=severity,
        limit=limit,
        offset=skip,
    )


@router.get("/alerts", response_model=schemas.SecurityAlertsResponse)
def check_security_alerts(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.SecurityAlertsResponse:
    """
    Check for current security alerts (admin only).

    Analyzes recent audit logs to detect suspicious patterns like:
    - Brute force login attempts
    - Mass data exports
    - Unusual admin access patterns
    """
    return SecurityAuditService.get_security_alerts_response(db)


# ============================================================================
# Privacy Incident Endpoints
# ============================================================================


@router.get("/incidents", response_model=schemas.IncidentListResponse)
def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    skip: PaginationSkip = 0,
    limit: PaginationLimitLarge = 50,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.IncidentListResponse:
    """
    List privacy incidents (admin only).

    Privacy incident register as required by Law 25 Article 3.6.
    """
    return IncidentService.list_incidents_response(
        db=db,
        status=status,
        severity=severity,
        limit=limit,
        offset=skip,
    )


@router.get("/incidents/pending-notifications", response_model=dict)
def get_pending_notifications(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """
    Get incidents requiring notifications (admin only).

    Returns incidents that still need CAI or user notifications.
    """
    return IncidentService.get_incidents_requiring_notification(db)


@router.get("/incidents/{incident_id}", response_model=schemas.IncidentDetail)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.IncidentDetail:
    """
    Get full details of a privacy incident (admin only).
    """
    detail = IncidentService.get_incident_detail(db, incident_id)
    if not detail:
        raise NotFoundException("Incident not found")
    return detail


@router.post("/incidents", response_model=schemas.IncidentCreateResponse)
def create_incident(
    incident_data: schemas.IncidentCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.IncidentCreateResponse:
    """
    Create a new privacy incident (admin only).

    Creates a new entry in the privacy incident register.
    """
    user_id: int = current_user.id  # type: ignore[assignment]

    return IncidentService.create_incident_response(
        db=db,
        incident_type=incident_data.incident_type,
        severity=incident_data.severity,
        title=incident_data.title,
        description=incident_data.description,
        occurred_at=incident_data.occurred_at,
        affected_users=incident_data.affected_user_ids,
        data_types=incident_data.data_types,
        reported_by=user_id,
    )


@router.put(
    "/incidents/{incident_id}/status",
    response_model=schemas.IncidentStatusUpdateResponse,
)
def update_incident_status(
    incident_id: int,
    status_update: schemas.IncidentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.IncidentStatusUpdateResponse:
    """
    Update incident status (admin only).

    Valid statuses: open, investigating, contained, mitigated, closed
    """
    try:
        return IncidentService.update_incident_status_response(
            db=db,
            incident_id=incident_id,
            status=status_update.status,
            notes=status_update.notes,
        )
    except ValueError as e:
        raise NotFoundException(str(e))


@router.post(
    "/incidents/{incident_id}/notify-cai",
    response_model=schemas.CAINotificationResponse,
)
def record_cai_notification(
    incident_id: int,
    reference_number: Optional[str] = Query(None, description="CAI reference number"),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.CAINotificationResponse:
    """
    Record CAI notification for an incident (admin only).

    Records that the Commission d'accès à l'information has been notified
    as required by Law 25 Article 3.6 for serious breaches.
    """
    try:
        return IncidentService.record_cai_notification_response(
            db=db,
            incident_id=incident_id,
            reference_number=reference_number,
        )
    except ValueError as e:
        raise NotFoundException(str(e))


@router.post(
    "/incidents/{incident_id}/notify-users",
    response_model=schemas.UserNotificationResponse,
)
def record_user_notifications(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> schemas.UserNotificationResponse:
    """
    Record user notifications for an incident (admin only).

    Records that affected users have been notified
    as required by Law 25 Article 3.6.
    """
    try:
        return IncidentService.record_user_notifications_response(
            db=db,
            incident_id=incident_id,
        )
    except ValueError as e:
        raise NotFoundException(str(e))
