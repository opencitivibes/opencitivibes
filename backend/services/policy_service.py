"""
Policy Version Service for Law 25 Compliance.

Manages policy versions and re-consent requirements.

Law 25 Articles:
- Article 8.1: Inform users of policy changes
- Article 9: Obtain explicit consent
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import schemas
from models.config import settings
from repositories import db_models
from repositories.policy_repository import PolicyRepository


class PolicyService:
    """Service for managing policy versions and consent."""

    @staticmethod
    def get_current_versions() -> dict[str, str]:
        """Get current active policy versions from settings."""
        return {
            "privacy": settings.PRIVACY_POLICY_VERSION,
            "terms": settings.TERMS_VERSION,
        }

    @staticmethod
    def check_requires_reconsent(
        db: Session, user: db_models.User
    ) -> schemas.ReconsentCheck:
        """
        Check if user needs to re-consent to updated policies.

        Args:
            db: Database session
            user: User to check

        Returns:
            ReconsentCheck with status for each policy type
        """
        current = PolicyService.get_current_versions()

        return schemas.ReconsentCheck(
            requires_privacy_reconsent=user.consent_privacy_version
            != current["privacy"],
            requires_terms_reconsent=user.consent_terms_version != current["terms"],
            current_privacy_version=current["privacy"],
            current_terms_version=current["terms"],
            user_privacy_version=user.consent_privacy_version,
            user_terms_version=user.consent_terms_version,
        )

    @staticmethod
    def get_policy_changelog(
        db: Session,
        policy_type: str,
        since_version: Optional[str] = None,
    ) -> schemas.PolicyChangelogResponse:
        """
        Get changelog of policy versions since a specific version.

        Useful for showing users what changed since they last consented.

        Args:
            db: Database session
            policy_type: 'privacy' or 'terms'
            since_version: Show changes after this version (optional)

        Returns:
            List of policy version changes
        """
        policy_repo = PolicyRepository(db)
        since_date = None

        if since_version:
            # Get effective date of since_version
            since = policy_repo.get_policy_version(policy_type, since_version)
            if since:
                since_date = since.effective_date

        versions = policy_repo.get_policy_versions(policy_type, since_date)

        return schemas.PolicyChangelogResponse(
            policy_type=policy_type,
            versions=[
                schemas.PolicyVersionInfo(
                    version=v.version,
                    effective_date=v.effective_date,
                    summary_en=v.summary_en,
                    summary_fr=v.summary_fr,
                    requires_reconsent=v.requires_reconsent,
                )
                for v in versions
            ],
        )

    @staticmethod
    def record_reconsent(
        db: Session,
        user: db_models.User,
        policy_type: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Record user's re-consent to updated policy.

        Args:
            db: Database session
            user: User giving consent
            policy_type: 'privacy' or 'terms'
            ip_address: Client IP address
            user_agent: Client user agent
        """
        now = datetime.now(timezone.utc)
        current = PolicyService.get_current_versions()

        if policy_type == "privacy":
            user.consent_privacy_accepted = True
            user.consent_privacy_version = current["privacy"]
            user.consent_timestamp = now
        elif policy_type == "terms":
            user.consent_terms_accepted = True
            user.consent_terms_version = current["terms"]
            user.consent_timestamp = now

        # Log the re-consent using repository
        policy_repo = PolicyRepository(db)
        policy_repo.add_consent_log(
            user_id=user.id,
            consent_type=policy_type,
            action="reconsented",
            policy_version=current.get(policy_type),
            ip_address=ip_address,
            user_agent=user_agent,
        )
