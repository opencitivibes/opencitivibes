"""
Parental Consent Service

Law 25 (Quebec) compliance for minors under 14.
Manages the parental consent workflow including:
- Token generation and email sending
- Consent verification and decision processing
- Account activation/deletion based on consent
- Cleanup of expired consents

All database operations go through repositories (architecture compliance).
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from sqlalchemy.orm import Session

import repositories.db_models as db_models
from helpers.age_utils import calculate_age
from models.exceptions import (
    ConsentAlreadyGrantedException,
    ConsentAlreadyProcessedException,
    ConsentNotRequiredException,
    ConsentResendRateLimitException,
    ConsentTokenExpiredException,
    ConsentTokenNotFoundException,
    NotFoundException,
)
from repositories.parental_consent_repository import ParentalConsentRepository
from repositories.user_repository import UserRepository


# Constants
CONSENT_TOKEN_BYTES = 32  # 256-bit token
TOKEN_EXPIRY_DAYS = 7  # Token expires after 7 days
MAX_RESENDS_PER_DAY = 3  # Rate limit for resend requests
GRACE_PERIOD_DAYS = 30  # Days before deleting denied accounts


class ParentalConsentService:
    """Service for managing parental consent workflow (Law 25 compliance)."""

    @staticmethod
    def _generate_token() -> tuple[str, str]:
        """
        Generate a secure consent token and its hash.

        Returns:
            Tuple of (plain_token, token_hash)
        """
        plain_token = secrets.token_urlsafe(CONSENT_TOKEN_BYTES)
        token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
        return plain_token, token_hash

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token using SHA-256."""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def initiate_consent_request(
        db: Session,
        user: db_models.User,
        parent_email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[db_models.ParentalConsentToken, str]:
        """
        Initiate parental consent request for a minor.

        Creates consent token, sends email to parent.

        Args:
            db: Database session
            user: User requiring parental consent
            parent_email: Parent/guardian email address
            ip_address: Client IP for audit log
            user_agent: Client user agent for audit log

        Returns:
            Tuple of (ParentalConsentToken, plain_token for email)

        Raises:
            ConsentNotRequiredException: If user doesn't require consent
            ConsentAlreadyGrantedException: If consent already granted
        """
        # Validate user requires consent
        if not user.requires_parental_consent:
            raise ConsentNotRequiredException()

        if user.parental_consent_status == "granted":
            raise ConsentAlreadyGrantedException()

        consent_repo = ParentalConsentRepository(db)
        user_repo = UserRepository(db)

        # Invalidate any existing active tokens
        consent_repo.invalidate_for_user(user.id)

        # Generate new token
        plain_token, token_hash = ParentalConsentService._generate_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS)

        # Create token in database
        token = consent_repo.create_token(
            pending_user_id=user.id,
            token_hash=token_hash,
            parent_email=parent_email,
            expires_at=expires_at,
        )

        # Update user's parent email and status
        user.parent_email = parent_email
        user.parental_consent_status = "pending"
        user_repo.update(user)

        # Log the request
        consent_repo.create_log(
            user_id=user.id,
            action="request_sent",
            parent_email=parent_email,
            token_id=token.id,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            notes=f"Token expires at {expires_at.isoformat()}",
        )

        # Send email to parent (handled by caller to keep service layer clean)
        return token, plain_token

    @staticmethod
    def get_consent_details(
        db: Session,
        token: str,
    ) -> dict:
        """
        Get consent request details for parent viewing.

        Args:
            db: Database session
            token: Plain consent token from email link

        Returns:
            Dictionary with consent request details (safe for display)

        Raises:
            ConsentTokenNotFoundException: If token not found
            ConsentTokenExpiredException: If token expired
            ConsentAlreadyProcessedException: If already used
        """
        token_hash = ParentalConsentService._hash_token(token)
        consent_repo = ParentalConsentRepository(db)

        db_token = consent_repo.get_by_hash(token_hash)
        if not db_token:
            raise ConsentTokenNotFoundException()

        # Check if already used
        if db_token.used_at is not None:
            raise ConsentAlreadyProcessedException()

        # Check if expired
        now = datetime.now(timezone.utc)
        if db_token.expires_at <= now:
            raise ConsentTokenExpiredException()

        # Get user info (safe subset only)
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(db_token.pending_user_id)
        if not user:
            raise NotFoundException("User not found")

        # Calculate age at registration
        age = None
        if user.date_of_birth:
            age = calculate_age(user.date_of_birth)

        return {
            "child_username": user.username,
            "child_email": user.email,
            "child_age": age,
            "child_display_name": user.display_name,
            "requested_at": db_token.created_at,
            "expires_at": db_token.expires_at,
            "parent_email": db_token.parent_email,
            "data_collected": [
                "Email address",
                "Username and display name",
                "Ideas, comments, and votes submitted",
                "Activity timestamps",
                "IP addresses (for security only)",
            ],
            "data_purposes": [
                "Civic engagement and community participation",
                "Moderation and platform safety",
            ],
            "retention_period": "Account lifetime + 30 days after deletion",
            "parent_rights": [
                "Access child's data (via account or data export)",
                "Rectify inaccurate information",
                "Delete account at any time",
                "Withdraw consent (results in account deletion)",
            ],
        }

    @staticmethod
    def process_consent_decision(
        db: Session,
        token: str,
        decision: Literal["granted", "denied"],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> db_models.User:
        """
        Process parent's consent decision.

        If granted: activates account.
        If denied: marks for deletion.

        Args:
            db: Database session
            token: Plain consent token from email link
            decision: "granted" or "denied"
            ip_address: Parent's IP address for audit
            user_agent: Parent's browser for audit

        Returns:
            Updated user object

        Raises:
            ConsentTokenNotFoundException: If token not found
            ConsentTokenExpiredException: If token expired
            ConsentAlreadyProcessedException: If already used
        """
        token_hash = ParentalConsentService._hash_token(token)
        consent_repo = ParentalConsentRepository(db)

        db_token = consent_repo.get_by_hash(token_hash)
        if not db_token:
            raise ConsentTokenNotFoundException()

        if db_token.used_at is not None:
            raise ConsentAlreadyProcessedException()

        now = datetime.now(timezone.utc)
        if db_token.expires_at <= now:
            raise ConsentTokenExpiredException()

        # Get user
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(db_token.pending_user_id)
        if not user:
            raise NotFoundException("User not found")

        # Mark token as used
        truncated_ua = user_agent[:500] if user_agent else None
        consent_repo.mark_used(
            token=db_token,
            decision=decision,
            ip_address=ip_address,
            user_agent=truncated_ua,
        )

        # Update user based on decision
        if decision == "granted":
            user.parental_consent_status = "granted"
            user.parental_consent_granted_at = now
            user.parental_consent_proof_id = token_hash[:32]
            user.is_active = True
            action = "consent_granted"
            notes = "Account activated"
        else:  # denied
            user.parental_consent_status = "denied"
            user.is_active = False
            action = "consent_denied"
            notes = f"Account scheduled for deletion in {GRACE_PERIOD_DAYS} days"

        user_repo.update(user)

        # Log the decision
        consent_repo.create_log(
            user_id=user.id,
            action=action,
            parent_email=db_token.parent_email,
            token_id=db_token.id,
            ip_address=ip_address,
            user_agent=truncated_ua,
            notes=notes,
        )

        return user

    @staticmethod
    def grant_consent(
        db: Session,
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> db_models.User:
        """
        Grant parental consent (wrapper for process_consent_decision).

        Args:
            db: Database session
            token: Plain consent token
            ip_address: Parent's IP address
            user_agent: Parent's browser

        Returns:
            Activated user object
        """
        return ParentalConsentService.process_consent_decision(
            db=db,
            token=token,
            decision="granted",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def deny_consent(
        db: Session,
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> db_models.User:
        """
        Deny parental consent (wrapper for process_consent_decision).

        Args:
            db: Database session
            token: Plain consent token
            ip_address: Parent's IP address
            user_agent: Parent's browser

        Returns:
            User object marked for deletion
        """
        return ParentalConsentService.process_consent_decision(
            db=db,
            token=token,
            decision="denied",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def resend_consent_request(
        db: Session,
        user_id: int,
        new_parent_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[db_models.ParentalConsentToken, str]:
        """
        Resend consent request email.

        Invalidates old tokens, creates new one.

        Args:
            db: Database session
            user_id: User ID requiring consent
            new_parent_email: New parent email (optional, uses existing if not provided)
            ip_address: Client IP for audit
            user_agent: Client user agent for audit

        Returns:
            Tuple of (new token, plain token for email)

        Raises:
            NotFoundException: If user not found
            ConsentNotRequiredException: If consent not required
            ConsentAlreadyGrantedException: If consent already granted
            ConsentResendRateLimitException: If too many resends
        """
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        if not user.requires_parental_consent:
            raise ConsentNotRequiredException()

        if user.parental_consent_status == "granted":
            raise ConsentAlreadyGrantedException()

        # Check rate limit (max 3 resends per day)
        consent_repo = ParentalConsentRepository(db)
        logs = consent_repo.get_logs_for_user(user_id)

        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)

        resend_count = sum(
            1
            for log in logs
            if log.action in ("request_sent", "request_resent")
            and log.created_at >= one_day_ago
        )

        if resend_count >= MAX_RESENDS_PER_DAY:
            raise ConsentResendRateLimitException()

        # Use new parent email or existing
        parent_email = new_parent_email or str(user.parent_email)
        if not parent_email:
            raise ConsentNotRequiredException(
                "No parent email on file. Please provide parent email."
            )

        # Invalidate old tokens
        consent_repo.invalidate_for_user(user_id)

        # Generate new token
        plain_token, token_hash = ParentalConsentService._generate_token()
        expires_at = now + timedelta(days=TOKEN_EXPIRY_DAYS)

        # Create new token
        token = consent_repo.create_token(
            pending_user_id=user_id,
            token_hash=token_hash,
            parent_email=parent_email,
            expires_at=expires_at,
        )

        # Update user's parent email if changed
        if new_parent_email:
            user.parent_email = new_parent_email
            user_repo.update(user)

        # Log the resend
        consent_repo.create_log(
            user_id=user_id,
            action="request_resent",
            parent_email=parent_email,
            token_id=token.id,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            notes=f"Resend #{resend_count + 1} today. Token expires at {expires_at.isoformat()}",
        )

        return token, plain_token

    @staticmethod
    def handle_expired_consents(db: Session) -> int:
        """
        Mark expired consent requests.

        Called by scheduled task to update users whose consent
        tokens have expired without a decision.

        Args:
            db: Database session

        Returns:
            Number of expired consents processed
        """
        consent_repo = ParentalConsentRepository(db)
        user_repo = UserRepository(db)

        expired_tokens = consent_repo.get_expired()
        processed = 0

        for token in expired_tokens:
            user = user_repo.get_by_id(token.pending_user_id)
            if not user:
                continue

            # Only update if still pending
            if user.parental_consent_status == "pending":
                user.parental_consent_status = "expired"
                user_repo.update(user)

                # Log expiration
                consent_repo.create_log(
                    user_id=user.id,
                    action="consent_expired",
                    parent_email=token.parent_email,
                    token_id=token.id,
                    notes="Token expired without parent response",
                )
                processed += 1

        return processed

    @staticmethod
    def cleanup_denied_accounts(db: Session) -> int:
        """
        Anonymize/delete denied accounts past grace period.

        Called by scheduled task to permanently delete accounts
        where parental consent was denied and grace period has passed.

        Args:
            db: Database session

        Returns:
            Number of accounts cleaned up
        """
        consent_repo = ParentalConsentRepository(db)

        accounts = consent_repo.get_accounts_pending_deletion(
            grace_period_days=GRACE_PERIOD_DAYS
        )

        # For now, we just return the count - actual deletion
        # should go through the account deletion service
        # to ensure proper anonymization per Law 25
        return len(accounts)

    @staticmethod
    def get_consent_history(db: Session, user_id: int) -> list[dict]:
        """
        Get consent history for a user.

        Law 25 Compliance: Users/parents have the right to access
        all consent-related actions for their account.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of consent log entries
        """
        consent_repo = ParentalConsentRepository(db)
        logs = consent_repo.get_logs_for_user(user_id)

        return [
            {
                "action": log.action,
                "parent_email": log.parent_email,
                "created_at": log.created_at,
                "notes": log.notes,
            }
            for log in logs
        ]

    @staticmethod
    def get_user_consent_status(db: Session, user_id: int) -> dict:
        """
        Get current consent status for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Dictionary with consent status details

        Raises:
            NotFoundException: If user not found
        """
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        consent_repo = ParentalConsentRepository(db)
        active_token = consent_repo.get_active_for_user(user_id)

        return {
            "is_minor": user.is_minor,
            "requires_parental_consent": user.requires_parental_consent,
            "consent_status": user.parental_consent_status,
            "parent_email": user.parent_email,
            "consent_granted_at": user.parental_consent_granted_at,
            "has_pending_request": active_token is not None,
            "pending_request_expires_at": active_token.expires_at
            if active_token
            else None,
        }
