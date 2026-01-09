"""
Trusted Device Service for 2FA Remember Device feature.

Business logic for device trust management with Law 25 compliance:
- All IP addresses are anonymized before storage
- Explicit consent is logged to ConsentLog table
- Device tokens are cryptographically secure and stored as hashes
"""

import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from helpers.ip_utils import anonymize_ip
from models.config import settings
from models.exceptions import (
    InsufficientPermissionsException,
    TrustedDeviceLimitExceededException,
    TrustedDeviceNotFoundException,
    ValidationException,
)
from repositories.consent_log_repository import ConsentLogRepository
from repositories.trusted_device_repository import TrustedDeviceRepository
from services.security_audit_service import SecurityAuditService

if TYPE_CHECKING:
    import repositories.db_models as db_models


def sanitize_device_name(name: str) -> str:
    """
    Sanitize device name to prevent XSS attacks.

    Removes HTML tags and scripts, keeps only safe characters.

    Args:
        name: Raw device name input

    Returns:
        Sanitized device name
    """
    import html

    # HTML escape special characters
    sanitized = html.escape(name, quote=True)

    # Remove any remaining HTML-like patterns (belt and suspenders)
    sanitized = re.sub(r"<[^>]*>", "", sanitized)

    # Strip leading/trailing whitespace
    sanitized = sanitized.strip()

    return sanitized


class TrustedDeviceService:
    """Service for trusted device management."""

    # Security event types for audit logging
    EVENT_DEVICE_TRUSTED = "device_trusted"
    EVENT_DEVICE_REVOKED = "device_revoked"
    EVENT_ALL_DEVICES_REVOKED = "all_devices_revoked"
    EVENT_DEVICE_TRUST_VERIFIED = "device_trust_verified"
    EVENT_DEVICE_TRUST_FAILED = "device_trust_failed"

    @staticmethod
    def generate_device_token() -> str:
        """
        Generate a cryptographically secure device token.

        Uses secrets module for secure random generation.
        Returns base64url encoded token.

        Returns:
            Base64url encoded device token (URL-safe)
        """
        return secrets.token_urlsafe(settings.TOTP_DEVICE_TOKEN_LENGTH)

    @staticmethod
    def hash_device_token(token: str) -> str:
        """
        Hash a device token using SHA-256.

        Args:
            token: Plain device token

        Returns:
            Hex digest of SHA-256 hash
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_token_hash_constant_time(token: str, expected_hash: str) -> bool:
        """
        Verify a token against its hash using constant-time comparison.

        Prevents timing attacks by using hmac.compare_digest.

        Args:
            token: Plain device token to verify
            expected_hash: Expected SHA-256 hash

        Returns:
            True if token matches hash, False otherwise
        """
        actual_hash = TrustedDeviceService.hash_device_token(token)
        return hmac.compare_digest(actual_hash, expected_hash)

    @staticmethod
    def create_device_fingerprint(
        user_agent: str | None,
        ip_address: str | None,
    ) -> dict:
        """
        Create a device fingerprint from available signals.

        Extracts browser, OS, and platform information from user agent.
        Anonymizes IP to subnet for privacy compliance.

        Args:
            user_agent: User agent string
            ip_address: Client IP address (will be anonymized)

        Returns:
            Dictionary with device fingerprint data
        """
        fingerprint: dict = {
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Anonymize IP to subnet
        if ip_address:
            fingerprint["ip_subnet"] = anonymize_ip(ip_address)

        # Parse user agent
        if user_agent:
            fingerprint["user_agent_raw"] = user_agent[:500]
            parsed = TrustedDeviceService._parse_user_agent(user_agent)
            fingerprint.update(parsed)

        return fingerprint

    @staticmethod
    def _parse_user_agent(user_agent: str) -> dict:
        """
        Parse user agent string to extract browser, OS, and platform.

        Simple regex-based parsing. For production, consider using
        a dedicated library like user-agents or httpagentparser.

        Args:
            user_agent: User agent string

        Returns:
            Dictionary with browser, os, and platform info
        """
        result: dict = {}

        # Browser detection
        browser_patterns = [
            (r"Firefox/(\d+)", "Firefox"),
            (r"Edg/(\d+)", "Edge"),
            (r"Chrome/(\d+)", "Chrome"),
            (r"Safari/(\d+)", "Safari"),
            (r"Opera/(\d+)", "Opera"),
            (r"MSIE (\d+)", "Internet Explorer"),
            (r"Trident.*rv:(\d+)", "Internet Explorer"),
        ]
        for pattern, browser in browser_patterns:
            match = re.search(pattern, user_agent)
            if match:
                result["browser"] = browser
                result["browser_version"] = match.group(1)
                break

        # OS detection
        os_patterns = [
            (r"Windows NT 10", "Windows 10"),
            (r"Windows NT 6\.3", "Windows 8.1"),
            (r"Windows NT 6\.2", "Windows 8"),
            (r"Windows NT 6\.1", "Windows 7"),
            (r"Mac OS X (\d+[._]\d+)", "macOS"),
            (r"iPhone OS (\d+)", "iOS"),
            (r"iPad.*OS (\d+)", "iPadOS"),
            (r"Android (\d+)", "Android"),
            (r"Linux", "Linux"),
            (r"CrOS", "Chrome OS"),
        ]
        for pattern, os_name in os_patterns:
            match = re.search(pattern, user_agent)
            if match:
                result["os"] = os_name
                if match.lastindex:
                    result["os_version"] = match.group(1).replace("_", ".")
                break

        # Platform detection
        if "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent:
            result["platform"] = "mobile"
        elif "iPad" in user_agent or "Tablet" in user_agent:
            result["platform"] = "tablet"
        else:
            result["platform"] = "desktop"

        return result

    @staticmethod
    def generate_device_name(user_agent: str | None) -> str:
        """
        Generate a user-friendly device name from user agent.

        Args:
            user_agent: User agent string

        Returns:
            Device name like "Chrome on Windows 10"
        """
        if not user_agent:
            return "Unknown Device"

        parsed = TrustedDeviceService._parse_user_agent(user_agent)
        browser = parsed.get("browser", "Unknown Browser")
        os_name = parsed.get("os", "Unknown OS")

        return f"{browser} on {os_name}"

    @staticmethod
    def log_device_consent(
        db: Session,
        user_id: int,
        action: str,
        ip_address: str | None,
        user_agent: str | None,
        device_metadata: dict | None = None,
    ) -> None:
        """
        Log device trust consent to ConsentLog table.

        CRITICAL: IP address is anonymized before logging (Law 25 compliance).

        Args:
            db: Database session
            user_id: User ID
            action: Consent action ("granted" or "withdrawn")
            ip_address: Client IP address (will be anonymized)
            user_agent: Client user agent
            device_metadata: Optional device information
        """
        repo = ConsentLogRepository(db)

        # Anonymize IP before logging
        anonymized_ip = anonymize_ip(ip_address)

        # Create consent log entry
        repo.create_consent_log(
            user_id=user_id,
            consent_type="device_trust",
            action=action,
            policy_version=None,  # Not applicable for device trust
            ip_address=anonymized_ip,
        )

    @staticmethod
    def trust_device(
        db: Session,
        user_id: int,
        user_agent: str | None,
        ip_address: str | None,
        duration_days: int | None = None,
        custom_name: str | None = None,
        consent_given: bool = False,
    ) -> tuple[str, "db_models.TrustedDevice"]:
        """
        Trust a device for 2FA bypass.

        CRITICAL: consent_given MUST be True (explicit consent required - Law 25).

        Args:
            db: Database session
            user_id: User ID
            user_agent: Client user agent string
            ip_address: Client IP address (will be anonymized)
            duration_days: Trust duration in days (default from config)
            custom_name: Custom device name (optional)
            consent_given: User has explicitly consented (REQUIRED)

        Returns:
            Tuple of (plain_device_token, TrustedDevice record)

        Raises:
            ValidationException: If consent not given or duration exceeds max
            TrustedDeviceLimitExceededException: If max devices reached
        """
        # Verify explicit consent (Law 25 requirement)
        if not consent_given:
            raise ValidationException(
                "Explicit consent is required to trust this device (Law 25 compliance)"
            )

        # Set duration with bounds checking
        if duration_days is None:
            duration_days = settings.TOTP_DEVICE_TRUST_DEFAULT_DAYS

        if duration_days > settings.TOTP_DEVICE_TRUST_MAX_DAYS:
            raise ValidationException(
                f"Trust duration cannot exceed {settings.TOTP_DEVICE_TRUST_MAX_DAYS} days"
            )

        if duration_days < 1:
            raise ValidationException("Trust duration must be at least 1 day")

        # Check device limit
        repo = TrustedDeviceRepository(db)
        current_count = repo.get_user_active_device_count(user_id)
        if current_count >= settings.TOTP_MAX_TRUSTED_DEVICES_PER_USER:
            raise TrustedDeviceLimitExceededException(
                f"Maximum number of trusted devices reached "
                f"({settings.TOTP_MAX_TRUSTED_DEVICES_PER_USER})"
            )

        # Generate token and hash
        plain_token = TrustedDeviceService.generate_device_token()
        token_hash = TrustedDeviceService.hash_device_token(plain_token)

        # Create fingerprint
        fingerprint = TrustedDeviceService.create_device_fingerprint(
            user_agent, ip_address
        )

        # Generate or use custom device name (sanitized for XSS prevention)
        if custom_name:
            device_name = sanitize_device_name(custom_name)
        else:
            device_name = TrustedDeviceService.generate_device_name(user_agent)
        device_name = device_name[:100]  # Enforce max length

        # Anonymize IP for storage
        anonymized_ip = anonymize_ip(ip_address)

        # Create trusted device record
        device = repo.create_trusted_device(
            user_id=user_id,
            device_token_hash=token_hash,
            device_fingerprint=json.dumps(fingerprint),
            device_name=device_name,
            ip_address_subnet=anonymized_ip,
            user_agent=user_agent,
            duration_days=duration_days,
        )

        # Log consent (Law 25 compliance)
        TrustedDeviceService.log_device_consent(
            db=db,
            user_id=user_id,
            action="granted",
            ip_address=ip_address,
            user_agent=user_agent,
            device_metadata={"device_id": device.id, "device_name": device_name},
        )

        # Log security event
        SecurityAuditService.log_event(
            db=db,
            event_type=TrustedDeviceService.EVENT_DEVICE_TRUSTED,
            action="create",
            severity="info",
            user_id=user_id,
            ip_address=anonymized_ip,
            user_agent=user_agent,
            resource_type="trusted_device",
            resource_id=device.id,
            details={
                "device_name": device_name,
                "duration_days": duration_days,
            },
        )

        repo.commit()

        return (plain_token, device)

    @staticmethod
    def verify_trusted_device(
        db: Session,
        user_id: int,
        device_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """
        Verify if a device token is valid for bypassing 2FA.

        SECURITY FEATURES:
        - Constant-time token comparison (prevents timing attacks)
        - Device fingerprint validation (prevents stolen token reuse)
        - Token length validation (prevents DoS)
        - Security audit logging

        Updates last_used_at if valid.
        Logs security events for both success and failure.

        Args:
            db: Database session
            user_id: User ID
            device_token: Plain device token
            ip_address: Client IP for logging
            user_agent: Client user agent for logging

        Returns:
            True if device is trusted and valid, False otherwise
        """
        # SECURITY: Validate token length to prevent DoS
        if not device_token or len(device_token) > 500:
            return False

        token_hash = TrustedDeviceService.hash_device_token(device_token)
        repo = TrustedDeviceRepository(db)

        # Use constant-time comparison in repository lookup
        # Now returns the device object instead of boolean
        device = repo.verify_device_token(user_id, token_hash)

        anonymized_ip = anonymize_ip(ip_address)

        if device:
            # SECURITY: Validate device fingerprint matches current request
            fingerprint_valid = TrustedDeviceService._validate_fingerprint(
                device, user_agent
            )

            if not fingerprint_valid:
                # Log fingerprint mismatch as security warning
                SecurityAuditService.log_event(
                    db=db,
                    event_type="device_fingerprint_mismatch",
                    action="verify",
                    severity="warning",
                    user_id=user_id,
                    ip_address=anonymized_ip,
                    user_agent=user_agent,
                    resource_type="trusted_device",
                    resource_id=device.id,
                    details={
                        "result": "fingerprint_mismatch",
                        "stored_browser": TrustedDeviceService._get_stored_browser(
                            device
                        ),
                        "current_browser": TrustedDeviceService._parse_user_agent(
                            user_agent or ""
                        ).get("browser", "unknown"),
                    },
                )
                return False

            # Update last used timestamp
            repo.update_last_used(device.id)
            repo.commit()

            # Log success
            SecurityAuditService.log_event(
                db=db,
                event_type=TrustedDeviceService.EVENT_DEVICE_TRUST_VERIFIED,
                action="verify",
                severity="info",
                user_id=user_id,
                ip_address=anonymized_ip,
                user_agent=user_agent,
                resource_type="trusted_device",
                resource_id=device.id,
                details={"result": "success"},
            )
            return True
        else:
            # Log failure
            SecurityAuditService.log_event(
                db=db,
                event_type=TrustedDeviceService.EVENT_DEVICE_TRUST_FAILED,
                action="verify",
                severity="warning",
                user_id=user_id,
                ip_address=anonymized_ip,
                user_agent=user_agent,
                details={"result": "failed"},
            )
            return False

    @staticmethod
    def _validate_fingerprint(
        device: "db_models.TrustedDevice",
        current_user_agent: str | None,
    ) -> bool:
        """
        Validate that current request matches stored device fingerprint.

        SECURITY: Prevents stolen tokens from being used on different devices.
        Lenient matching: allows browser version changes but requires same browser.

        Args:
            device: Stored trusted device record
            current_user_agent: Current request's user agent

        Returns:
            True if fingerprint matches, False otherwise
        """
        if not current_user_agent:
            # No user agent to compare - allow (mobile apps may not send)
            return True

        stored_fingerprint = TrustedDeviceService._get_stored_browser(device)
        if not stored_fingerprint:
            # No stored fingerprint - allow (legacy devices)
            return True

        # Parse current user agent
        current_parsed = TrustedDeviceService._parse_user_agent(current_user_agent)
        current_browser = current_parsed.get("browser")

        if not current_browser:
            # Unknown browser - allow
            return True

        # Compare browser family (lenient: allows version changes)
        return stored_fingerprint == current_browser

    @staticmethod
    def _get_stored_browser(device: "db_models.TrustedDevice") -> str | None:
        """Extract browser from stored device fingerprint."""
        if not device.device_fingerprint:
            return None

        try:
            fingerprint = json.loads(device.device_fingerprint)
            return fingerprint.get("browser")
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def get_user_devices(
        db: Session,
        user_id: int,
        active_only: bool = True,
    ) -> list["db_models.TrustedDevice"]:
        """
        Get all trusted devices for a user.

        Args:
            db: Database session
            user_id: User ID
            active_only: If True, only return active devices

        Returns:
            List of TrustedDevice records
        """
        repo = TrustedDeviceRepository(db)
        return repo.get_user_devices(user_id, active_only=active_only)

    @staticmethod
    def rename_device(
        db: Session,
        user_id: int,
        device_id: int,
        new_name: str,
    ) -> "db_models.TrustedDevice":
        """
        Rename a trusted device.

        Args:
            db: Database session
            user_id: User ID (for ownership verification)
            device_id: Device ID to rename
            new_name: New device name

        Returns:
            Updated TrustedDevice record

        Raises:
            TrustedDeviceNotFoundException: If device not found
            InsufficientPermissionsException: If user doesn't own device
        """
        repo = TrustedDeviceRepository(db)
        device = repo.get_by_id(device_id)

        if not device:
            raise TrustedDeviceNotFoundException("Trusted device not found")

        if device.user_id != user_id:
            raise InsufficientPermissionsException(
                "You do not have permission to rename this device"
            )

        # Sanitize the name to prevent XSS
        sanitized_name = sanitize_device_name(new_name)
        if not sanitized_name:
            raise ValidationException("Device name cannot be empty after sanitization")

        repo.update_device_name(device_id, sanitized_name)
        repo.commit()
        repo.refresh(device)

        return device

    @staticmethod
    def revoke_device(
        db: Session,
        user_id: int,
        device_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Revoke a trusted device.

        CRITICAL: Logs consent withdrawal (Law 25 compliance).

        Args:
            db: Database session
            user_id: User ID (for ownership verification)
            device_id: Device ID to revoke
            ip_address: Client IP for logging
            user_agent: Client user agent for logging

        Raises:
            TrustedDeviceNotFoundException: If device not found
            InsufficientPermissionsException: If user doesn't own device
        """
        repo = TrustedDeviceRepository(db)
        device = repo.get_by_id(device_id)

        if not device:
            raise TrustedDeviceNotFoundException("Trusted device not found")

        if device.user_id != user_id:
            raise InsufficientPermissionsException(
                "You do not have permission to revoke this device"
            )

        device_name = device.device_name
        repo.revoke_device(device_id)

        # Log consent withdrawal (Law 25 compliance)
        TrustedDeviceService.log_device_consent(
            db=db,
            user_id=user_id,
            action="withdrawn",
            ip_address=ip_address,
            user_agent=user_agent,
            device_metadata={"device_id": device_id, "device_name": device_name},
        )

        anonymized_ip = anonymize_ip(ip_address)

        # Log security event
        SecurityAuditService.log_event(
            db=db,
            event_type=TrustedDeviceService.EVENT_DEVICE_REVOKED,
            action="revoke",
            severity="info",
            user_id=user_id,
            ip_address=anonymized_ip,
            user_agent=user_agent,
            resource_type="trusted_device",
            resource_id=device_id,
            details={"device_name": device_name},
        )

        repo.commit()

    @staticmethod
    def revoke_all_devices(
        db: Session,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> int:
        """
        Revoke all trusted devices for a user.

        CRITICAL: Logs consent withdrawal for all devices (Law 25 compliance).

        Args:
            db: Database session
            user_id: User ID
            ip_address: Client IP for logging
            user_agent: Client user agent for logging

        Returns:
            Number of devices revoked
        """
        repo = TrustedDeviceRepository(db)

        # Get count before revoking
        devices = repo.get_user_devices(user_id, active_only=True)
        count = len(devices)

        if count == 0:
            return 0

        # Revoke all devices
        repo.revoke_all_user_devices(user_id)

        # Log consent withdrawal for all devices (Law 25 compliance)
        TrustedDeviceService.log_device_consent(
            db=db,
            user_id=user_id,
            action="withdrawn",
            ip_address=ip_address,
            user_agent=user_agent,
            device_metadata={"revoked_count": count, "action": "revoke_all"},
        )

        anonymized_ip = anonymize_ip(ip_address)

        # Log security event
        SecurityAuditService.log_event(
            db=db,
            event_type=TrustedDeviceService.EVENT_ALL_DEVICES_REVOKED,
            action="revoke_all",
            severity="info",
            user_id=user_id,
            ip_address=anonymized_ip,
            user_agent=user_agent,
            details={"devices_revoked": count},
        )

        repo.commit()

        return count

    @staticmethod
    def cleanup_expired_devices(db: Session) -> int:
        """
        Mark expired devices as inactive.

        For use by scheduled background tasks.

        Args:
            db: Database session

        Returns:
            Number of devices marked as expired
        """
        repo = TrustedDeviceRepository(db)
        return repo.cleanup_expired_devices()

    @staticmethod
    def delete_old_revoked_devices(db: Session) -> int:
        """
        Permanently delete revoked devices older than retention period.

        Law 25 compliance: Revoked devices are retained for audit purposes
        for a limited time (default 7 days) then permanently deleted.

        Args:
            db: Database session

        Returns:
            Number of devices permanently deleted
        """
        repo = TrustedDeviceRepository(db)
        return repo.delete_old_revoked_devices(
            retention_days=settings.TOTP_REVOKED_DEVICE_RETENTION_DAYS
        )
