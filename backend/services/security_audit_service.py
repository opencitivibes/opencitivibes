"""
Security Audit Service for Law 25 Compliance.

Logs security-relevant events and enables breach detection.
Required by Article 3.5 of Law 25 for detection of privacy incidents.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

import models.schemas as schemas
from models.config import settings
from models.notification_types import NotificationType
from repositories import db_models
from repositories.security_audit_repository import SecurityAuditRepository
from services.notification_service import NotificationService


class SecurityEventType:
    """Standard security event types for audit logging."""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_BLOCKED = "login_blocked"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"  # nosec B105 - event type, not password  # pragma: allowlist secret
    PASSWORD_RESET_REQUESTED = "password_reset_requested"  # nosec B105 # pragma: allowlist secret
    EMAIL_CHANGED = "email_changed"
    TWO_FA_ENABLED = "2fa_enabled"
    TWO_FA_DISABLED = "2fa_disabled"
    DATA_EXPORT = "data_export"
    ACCOUNT_DELETED = "account_deleted"
    ADMIN_ACCESS_PII = "admin_access_pii"
    ADMIN_USER_MODIFIED = "admin_user_modified"
    ADMIN_USER_DELETED = "admin_user_deleted"
    ADMIN_BULK_OPERATION = "admin_bulk_operation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class SecurityAuditService:
    """Service for security audit logging and monitoring."""

    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        action: str,
        severity: str = "info",
        user_id: Optional[int] = None,
        target_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        details: Optional[dict] = None,
        success: bool = True,
    ) -> db_models.SecurityAuditLog:
        """
        Log a security event to the audit log.

        Args:
            db: Database session
            event_type: Type of security event (use SecurityEventType constants)
            action: Action taken (e.g., 'view', 'create', 'update', 'delete')
            severity: Severity level ('info', 'warning', 'critical')
            user_id: User who performed the action
            target_user_id: User affected by the action (e.g., for admin actions)
            ip_address: Client IP address
            user_agent: Client user agent string
            resource_type: Type of resource affected ('user', 'idea', 'comment')
            resource_id: ID of the resource affected
            details: Additional details as dictionary
            success: Whether the action succeeded

        Returns:
            Created SecurityAuditLog entry
        """
        log_entry = db_models.SecurityAuditLog(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            target_user_id=target_user_id,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=json.dumps(details) if details else None,
            success=success,
        )

        repo = SecurityAuditRepository(db)
        created = repo.create(log_entry)

        # Log to structured logger as well
        log_data = {
            "event_type": event_type,
            "action": action,
            "user_id": user_id,
            "ip_address": ip_address,
            "success": success,
        }

        if severity == "critical":
            logger.critical(f"Security event: {event_type}", extra=log_data)
        elif severity == "warning":
            logger.warning(f"Security event: {event_type}", extra=log_data)
        else:
            logger.info(f"Security event: {event_type}", extra=log_data)

        return created

    @staticmethod
    def detect_suspicious_patterns(db: Session) -> list[dict]:
        """
        Detect suspicious activity patterns.

        Checks for:
        - Multiple failed logins from same IP (brute force)
        - Mass data exports by single user
        - Unusual admin PII access patterns

        Args:
            db: Database session

        Returns:
            List of detected suspicious pattern alerts
        """
        alerts: list[dict] = []
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        repo = SecurityAuditRepository(db)

        # Check for brute force attempts
        failed_logins = repo.get_failed_logins_by_ip(
            event_type=SecurityEventType.LOGIN_FAILED,
            since=one_hour_ago,
            threshold=settings.SECURITY_BRUTE_FORCE_THRESHOLD,
        )

        for ip, count in failed_logins:
            alerts.append(
                {
                    "type": "brute_force_attempt",
                    "severity": "critical",
                    "ip_address": ip,
                    "failed_attempts": count,
                    "detected_at": now.isoformat(),
                }
            )

        # Check for mass data exports
        mass_exports = repo.get_exports_by_user(
            event_type=SecurityEventType.DATA_EXPORT,
            since=one_hour_ago,
            threshold=settings.SECURITY_MASS_EXPORT_THRESHOLD,
        )

        for user_id, count in mass_exports:
            alerts.append(
                {
                    "type": "mass_data_export",
                    "severity": "warning",
                    "user_id": user_id,
                    "export_count": count,
                    "detected_at": now.isoformat(),
                }
            )

        # Check for unusual admin PII access
        admin_access = repo.get_admin_access_by_user(
            event_type=SecurityEventType.ADMIN_ACCESS_PII,
            since=one_hour_ago,
            threshold=settings.SECURITY_ADMIN_ACCESS_THRESHOLD,
        )

        for admin_id, count in admin_access:
            alerts.append(
                {
                    "type": "unusual_admin_access",
                    "severity": "warning",
                    "admin_user_id": admin_id,
                    "access_count": count,
                    "detected_at": now.isoformat(),
                }
            )

        return alerts

    @staticmethod
    def get_security_alerts_response(db: Session) -> schemas.SecurityAlertsResponse:
        """
        Get current security alerts as schema response.

        Args:
            db: Database session

        Returns:
            SecurityAlertsResponse schema with alerts and count
        """
        alerts = SecurityAuditService.detect_suspicious_patterns(db)
        return schemas.SecurityAlertsResponse(alerts=alerts, count=len(alerts))

    @staticmethod
    def get_audit_logs_response(
        db: Session,
        event_type: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[schemas.SecurityAuditLogResponse]:
        """
        Get audit logs with filters, returning schema objects.

        Args:
            db: Database session
            event_type: Filter by event type
            user_id: Filter by user ID
            ip_address: Filter by IP address
            severity: Filter by severity level
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum records to return
            offset: Number of records to skip

        Returns:
            List of SecurityAuditLogResponse schema objects
        """
        repo = SecurityAuditRepository(db)
        logs = repo.get_logs(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            severity=severity,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        return [
            schemas.SecurityAuditLogResponse(
                id=log.id,
                event_type=log.event_type,
                severity=log.severity,
                user_id=log.user_id,
                action=log.action,
                ip_address=log.ip_address,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                success=log.success,
                created_at=log.created_at,
            )
            for log in logs
        ]

    @staticmethod
    def count_audit_logs(
        db: Session,
        event_type: Optional[str] = None,
        user_id: Optional[int] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Count audit logs matching filters."""
        repo = SecurityAuditRepository(db)
        return repo.count_logs(
            event_type=event_type,
            user_id=user_id,
            severity=severity,
            start_date=start_date,
            end_date=end_date,
        )

    @staticmethod
    def send_security_alert(
        title: str,
        message: str,
        priority: str = "high",
    ) -> None:
        """
        Send a security alert notification to admins.

        Args:
            title: Alert title
            message: Alert message content
            priority: Notification priority ('high' or 'max' for critical)
        """
        NotificationService.send_fire_and_forget(
            NotificationType.CRITICAL,
            title,
            message,
            priority_override=priority,
        )
