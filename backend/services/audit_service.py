"""Service for audit logging of sensitive operations."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AuditAction:
    """Audit action types for official-related operations."""

    OFFICIAL_GRANTED = "official_granted"
    OFFICIAL_REVOKED = "official_revoked"
    OFFICIAL_TITLE_UPDATED = "official_title_updated"
    OFFICIAL_REQUEST_REJECTED = "official_request_rejected"
    ANALYTICS_VIEWED = "analytics_viewed"
    DATA_EXPORTED = "data_exported"


class AuditService:
    """Service for audit logging."""

    @staticmethod
    def log(
        user_id: int,
        action: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Log an audit event.

        For MVP, logs to application logger.
        Can be extended to store in database.

        Args:
            user_id: ID of the user performing the action.
            action: Type of action performed.
            target_type: Type of entity being acted upon.
            target_id: ID of the entity being acted upon.
            details: Additional details about the action.
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "details": details,
        }

        logger.info("AUDIT: %s", json.dumps(log_entry))
