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
    # Trusted Device Events (2FA Remember Device)
    DEVICE_TRUSTED = "device_trusted"
    DEVICE_REVOKED = "device_revoked"
    ALL_DEVICES_REVOKED = "all_devices_revoked"
    DEVICE_TRUST_VERIFIED = "device_trust_verified"
    DEVICE_TRUST_FAILED = "device_trust_failed"


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

    # =========================================================================
    # Login Event Tracking Methods (Security Audit Phase 1)
    # =========================================================================

    @staticmethod
    def log_login_success(
        db: Session,
        user_id: int,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> db_models.LoginEvent:
        """
        Log a successful login event to the LoginEvent table.

        Also logs to SecurityAuditLog for comprehensive audit trail.
        IP addresses are anonymized at storage time for Law 25 compliance.

        Args:
            db: Database session
            user_id: ID of the user who logged in
            email: User's email address
            ip_address: Client IP address (will be anonymized)
            user_agent: Browser user agent
            metadata_json: Additional metadata (e.g., 2FA method used)

        Returns:
            Created LoginEvent entry
        """
        from helpers.ip_utils import anonymize_ip
        from repositories.login_event_repository import LoginEventRepository

        # Anonymize IP address for privacy compliance (Law 25)
        anon_ip = anonymize_ip(ip_address)

        repo = LoginEventRepository(db)
        event = repo.create_event(
            event_type=db_models.LoginEventType.LOGIN_SUCCESS,
            user_id=user_id,
            email=email,
            ip_address=anon_ip,
            user_agent=user_agent,
            metadata_json=metadata_json,
        )

        # Also log to general security audit log (with anonymized IP)
        SecurityAuditService.log_event(
            db=db,
            event_type=SecurityEventType.LOGIN_SUCCESS,
            action="login",
            user_id=user_id,
            ip_address=anon_ip,
            user_agent=user_agent,
            success=True,
        )

        return event

    @staticmethod
    def log_login_failure(
        db: Session,
        email: str,
        failure_reason: db_models.LoginFailureReason,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        user_id: Optional[int] = None,
        metadata_json: Optional[str] = None,
    ) -> db_models.LoginEvent:
        """
        Log a failed login attempt to the LoginEvent table.

        Also logs to SecurityAuditLog for comprehensive audit trail.
        IP addresses are anonymized and emails are hashed for failed attempts
        from unknown users to prevent user enumeration (V4 security fix).

        Args:
            db: Database session
            email: Email used in the attempt (hashed if user unknown)
            failure_reason: Why the login failed
            ip_address: Client IP address (will be anonymized)
            user_agent: Browser user agent
            user_id: User ID if the user exists but auth failed
            metadata_json: Additional metadata

        Returns:
            Created LoginEvent entry
        """
        from helpers.ip_utils import anonymize_ip, hash_email_for_audit
        from repositories.login_event_repository import LoginEventRepository

        # Anonymize IP address for privacy compliance (Law 25)
        anon_ip = anonymize_ip(ip_address)

        # For failed logins without a user_id (user enumeration risk),
        # hash the email to prevent revealing valid email addresses
        stored_email = email
        if user_id is None:
            stored_email = hash_email_for_audit(email)

        repo = LoginEventRepository(db)
        event = repo.create_event(
            event_type=db_models.LoginEventType.LOGIN_FAILED,
            email=stored_email,
            user_id=user_id,
            ip_address=anon_ip,
            user_agent=user_agent,
            failure_reason=failure_reason,
            metadata_json=metadata_json,
        )

        # Also log to general security audit log (with anonymized/hashed data)
        SecurityAuditService.log_event(
            db=db,
            event_type=SecurityEventType.LOGIN_FAILED,
            action="login",
            user_id=user_id,
            ip_address=anon_ip,
            user_agent=user_agent,
            details={"email": stored_email, "reason": failure_reason.value},
            success=False,
        )

        return event

    @staticmethod
    def log_logout(
        db: Session,
        user_id: int,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> db_models.LoginEvent:
        """
        Log a logout event to the LoginEvent table.

        IP addresses are anonymized at storage time for Law 25 compliance.

        Args:
            db: Database session
            user_id: ID of the user who logged out
            email: User's email address
            ip_address: Client IP address (will be anonymized)
            user_agent: Browser user agent

        Returns:
            Created LoginEvent entry
        """
        from helpers.ip_utils import anonymize_ip
        from repositories.login_event_repository import LoginEventRepository

        # Anonymize IP address for privacy compliance (Law 25)
        anon_ip = anonymize_ip(ip_address)

        repo = LoginEventRepository(db)
        event = repo.create_event(
            event_type=db_models.LoginEventType.LOGOUT,
            user_id=user_id,
            email=email,
            ip_address=anon_ip,
            user_agent=user_agent,
        )

        # Also log to general security audit log (with anonymized IP)
        SecurityAuditService.log_event(
            db=db,
            event_type=SecurityEventType.LOGOUT,
            action="logout",
            user_id=user_id,
            ip_address=anon_ip,
            user_agent=user_agent,
            success=True,
        )

        return event

    @staticmethod
    def log_password_reset_request(
        db: Session,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> db_models.LoginEvent:
        """
        Log a password reset request to the LoginEvent table.

        IP addresses are anonymized and emails are hashed for requests
        from unknown users to prevent user enumeration.

        Args:
            db: Database session
            email: Email for the reset request (hashed if user unknown)
            ip_address: Client IP address (will be anonymized)
            user_agent: Browser user agent
            user_id: User ID if user exists

        Returns:
            Created LoginEvent entry
        """
        from helpers.ip_utils import anonymize_ip, hash_email_for_audit
        from repositories.login_event_repository import LoginEventRepository

        # Anonymize IP address for privacy compliance (Law 25)
        anon_ip = anonymize_ip(ip_address)

        # For password reset without a user_id (user enumeration risk),
        # hash the email to prevent revealing valid email addresses
        stored_email = email
        if user_id is None:
            stored_email = hash_email_for_audit(email)

        repo = LoginEventRepository(db)
        event = repo.create_event(
            event_type=db_models.LoginEventType.PASSWORD_RESET_REQUEST,
            email=stored_email,
            user_id=user_id,
            ip_address=anon_ip,
            user_agent=user_agent,
        )

        # Also log to general security audit log (with anonymized/hashed data)
        SecurityAuditService.log_event(
            db=db,
            event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
            action="password_reset_request",
            user_id=user_id,
            ip_address=anon_ip,
            user_agent=user_agent,
            details={"email": stored_email},
            success=True,
        )

        return event

    @staticmethod
    def get_login_events_summary(db: Session) -> dict:
        """
        Get login event statistics for the admin dashboard.

        Returns aggregated data about login events in the last 24 hours.

        Args:
            db: Database session

        Returns:
            Dictionary containing login event statistics
        """
        from repositories.login_event_repository import LoginEventRepository

        repo = LoginEventRepository(db)

        # Get counts
        total_events = repo.count()
        successful_logins = repo.count_events_in_window(
            window_hours=24, event_type=db_models.LoginEventType.LOGIN_SUCCESS
        )
        failed_logins = repo.count_events_in_window(
            window_hours=24, event_type=db_models.LoginEventType.LOGIN_FAILED
        )
        unique_ips = repo.get_unique_ips_count(window_hours=24)

        # Calculate failure rate
        total_login_attempts = successful_logins + failed_logins
        if total_login_attempts > 0:
            failed_login_rate = (failed_logins / total_login_attempts) * 100
        else:
            failed_login_rate = 0.0

        # Get failure reasons
        failure_reasons = repo.get_failure_reason_counts(window_hours=24)
        top_failure_reasons = [
            {"reason": str(reason.value) if reason else "unknown", "count": count}
            for reason, count in failure_reasons
        ]

        # Get suspicious IPs
        suspicious_ip_data = repo.get_suspicious_ips(
            window_hours=24, failure_threshold=5, limit=10
        )
        suspicious_ips = [
            {"ip": ip, "failures": failures, "total": total}
            for ip, failures, total in suspicious_ip_data
        ]

        return {
            "total_events": total_events,
            "successful_logins_24h": successful_logins,
            "failed_logins_24h": failed_logins,
            "unique_ips_24h": unique_ips,
            "failed_login_rate": round(failed_login_rate, 2),
            "top_failure_reasons": top_failure_reasons,
            "suspicious_ips": suspicious_ips,
            "generated_at": datetime.now(timezone.utc),
        }

    @staticmethod
    def get_failed_attempts_for_email(
        db: Session, email: str, window_minutes: int = 15
    ) -> int:
        """
        Get the number of failed login attempts for an email.

        Useful for rate limiting before additional lockout measures.

        Args:
            db: Database session
            email: Email to check
            window_minutes: Time window to check

        Returns:
            Count of failed attempts
        """
        from repositories.login_event_repository import LoginEventRepository

        repo = LoginEventRepository(db)
        return repo.get_failed_attempts_count(
            email=email, window_minutes=window_minutes
        )

    @staticmethod
    def get_failed_attempts_for_ip(
        db: Session, ip_address: str, window_minutes: int = 15
    ) -> int:
        """
        Get the number of failed login attempts from an IP.

        Useful for IP-based rate limiting.

        Args:
            db: Database session
            ip_address: IP address to check
            window_minutes: Time window to check

        Returns:
            Count of failed attempts
        """
        from repositories.login_event_repository import LoginEventRepository

        repo = LoginEventRepository(db)
        return repo.get_failed_attempts_count(
            ip_address=ip_address, window_minutes=window_minutes
        )

    @staticmethod
    def cleanup_old_login_events(db: Session, retention_days: int = 90) -> int:
        """
        Remove login events older than the retention period.

        Should be called periodically (e.g., daily cron job).

        Args:
            db: Database session
            retention_days: Days to retain events

        Returns:
            Number of deleted events
        """
        from repositories.login_event_repository import LoginEventRepository

        repo = LoginEventRepository(db)
        return repo.cleanup_old_events(retention_days=retention_days)

    # =========================================================================
    # Admin API Methods (Security Audit Phase 2)
    # =========================================================================

    @staticmethod
    def get_security_events_list(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        event_type: Optional[str] = None,
        user_id: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> tuple[list[schemas.AdminSecurityEventItem], int]:
        """
        Get paginated list of security events for admin dashboard.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum records to return
            event_type: Optional filter by event type
            user_id: Optional filter by user ID
            since: Optional datetime filter

        Returns:
            Tuple of (events list, total count)
        """
        from helpers.time_utils import (
            format_relative_time,
            mask_ip_address,
            truncate_user_agent,
        )
        from repositories.login_event_repository import LoginEventRepository

        repo = LoginEventRepository(db)

        # Convert event_type string to enum if provided
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = db_models.LoginEventType(event_type)
            except ValueError:
                pass  # Invalid event type, ignore filter

        events = repo.get_events_with_filters(
            skip=skip,
            limit=limit,
            event_type=event_type_enum,
            user_id=user_id,
            since=since,
        )

        total = repo.count_events_with_filters(
            event_type=event_type_enum,
            user_id=user_id,
            since=since,
        )

        items = [
            schemas.AdminSecurityEventItem(
                id=e.id,
                user_id=e.user_id,
                email=e.email,
                event_type=e.event_type.value if e.event_type else "unknown",
                ip_address=mask_ip_address(e.ip_address),
                user_agent_short=truncate_user_agent(e.user_agent),
                failure_reason=(e.failure_reason.value if e.failure_reason else None),
                created_at=e.created_at,
                time_ago=format_relative_time(e.created_at),
            )
            for e in events
        ]

        return items, total

    @staticmethod
    def get_security_summary(db: Session) -> schemas.AdminSecuritySummary:
        """
        Get aggregated security statistics for the admin dashboard.

        Includes 24h stats, suspicious IPs, and recent admin logins.

        Args:
            db: Database session

        Returns:
            AdminSecuritySummary schema with all statistics
        """
        from helpers.time_utils import format_relative_time, mask_ip_address
        from repositories.login_event_repository import LoginEventRepository

        repo = LoginEventRepository(db)

        # Get 24h counts
        total_24h = repo.count_events_in_window(window_hours=24)
        successful_24h = repo.count_events_in_window(
            window_hours=24, event_type=db_models.LoginEventType.LOGIN_SUCCESS
        )
        failed_24h = repo.count_events_in_window(
            window_hours=24, event_type=db_models.LoginEventType.LOGIN_FAILED
        )
        unique_ips_24h = repo.get_unique_ips_count(window_hours=24)
        admin_logins_24h = repo.count_admin_logins(window_hours=24)

        # Get suspicious IPs (high failure rate in last 24h)
        suspicious_ip_data = repo.get_suspicious_ips(
            window_hours=24, failure_threshold=5, limit=10
        )
        suspicious_ips = [
            schemas.SuspiciousIPItem(
                ip=mask_ip_address(ip) or "unknown",
                failed_count=failures,
                last_attempt=None,  # We'll add this in future if needed
            )
            for ip, failures, total in suspicious_ip_data
        ]

        # Get recent admin logins
        admin_events = repo.get_admin_logins(window_hours=24, limit=5)
        recent_admin_logins = [
            schemas.RecentAdminLogin(
                email=e.email or "unknown",
                ip=mask_ip_address(e.ip_address) or "unknown",
                time_ago=format_relative_time(e.created_at),
            )
            for e in admin_events
        ]

        return schemas.AdminSecuritySummary(
            total_events_24h=total_24h,
            successful_logins_24h=successful_24h,
            failed_attempts_24h=failed_24h,
            unique_ips_24h=unique_ips_24h,
            admin_logins_24h=admin_logins_24h,
            suspicious_ips=suspicious_ips,
            recent_admin_logins=recent_admin_logins,
        )

    @staticmethod
    def get_events_for_user(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[schemas.AdminSecurityEventItem], int]:
        """
        Get login events for a specific user.

        Args:
            db: Database session
            user_id: User ID to filter by
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (events list, total count)
        """
        return SecurityAuditService.get_security_events_list(
            db=db,
            skip=skip,
            limit=limit,
            user_id=user_id,
        )

    @staticmethod
    def get_failed_attempts_list(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        hours: int = 24,
    ) -> tuple[list[schemas.AdminSecurityEventItem], int]:
        """
        Get recent failed login attempts only.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum records to return
            hours: Time window in hours

        Returns:
            Tuple of (events list, total count)
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        return SecurityAuditService.get_security_events_list(
            db=db,
            skip=skip,
            limit=limit,
            event_type=db_models.LoginEventType.LOGIN_FAILED.value,
            since=since,
        )

    @staticmethod
    def check_brute_force_risk(db: Session) -> list[schemas.BruteForceRiskItem]:
        """
        Detect potential brute force attack patterns.

        Checks for IPs with multiple failures in short windows.

        Args:
            db: Database session

        Returns:
            List of IPs showing brute force patterns
        """
        from helpers.time_utils import format_relative_time, mask_ip_address
        from repositories.login_event_repository import LoginEventRepository

        repo = LoginEventRepository(db)

        # Get IPs with 3+ failures in the last hour
        suspicious = repo.get_failed_attempts_by_ip_in_window(
            window_hours=1, min_failures=3, limit=20
        )

        return [
            schemas.BruteForceRiskItem(
                ip=mask_ip_address(ip) or "unknown",
                failed_count=count,
                last_attempt=(
                    format_relative_time(last_time) if last_time else "unknown"
                ),
                risk_level="high" if count >= 10 else "medium",
            )
            for ip, count, last_time in suspicious
        ]

    @staticmethod
    def trigger_cleanup(db: Session, retention_days: int = 90) -> dict:
        """
        Manually trigger cleanup of old login events.

        Args:
            db: Database session
            retention_days: Days to retain (default 90)

        Returns:
            Dict with cleanup results
        """
        deleted_count = SecurityAuditService.cleanup_old_login_events(
            db, retention_days=retention_days
        )

        logger.info(
            f"Manual cleanup triggered: deleted {deleted_count} events "
            f"older than {retention_days} days"
        )

        return {
            "deleted_count": deleted_count,
            "retention_days": retention_days,
            "triggered_at": datetime.now(timezone.utc),
        }
