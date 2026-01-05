"""Tests for PolicyService."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.config import settings
from repositories.db_models import ConsentLog, PolicyVersion, User
from services.policy_service import PolicyService


class TestGetCurrentVersions:
    """Tests for get_current_versions."""

    def test_returns_versions_from_settings(self) -> None:
        """Should return versions from settings."""
        versions = PolicyService.get_current_versions()

        assert versions["privacy"] == settings.PRIVACY_POLICY_VERSION
        assert versions["terms"] == settings.TERMS_VERSION


class TestCheckRequiresReconsent:
    """Tests for check_requires_reconsent."""

    def test_no_reconsent_when_versions_match(
        self, db: Session, test_user: User
    ) -> None:
        """Should not require reconsent when versions match."""
        # Set user versions to match settings
        test_user.consent_privacy_version = settings.PRIVACY_POLICY_VERSION
        test_user.consent_terms_version = settings.TERMS_VERSION
        db.commit()

        result = PolicyService.check_requires_reconsent(db, test_user)

        assert result.requires_privacy_reconsent is False
        assert result.requires_terms_reconsent is False
        assert result.current_privacy_version == settings.PRIVACY_POLICY_VERSION
        assert result.current_terms_version == settings.TERMS_VERSION

    def test_requires_privacy_reconsent_when_version_differs(
        self, db: Session, test_user: User
    ) -> None:
        """Should require privacy reconsent when version differs."""
        test_user.consent_privacy_version = "0.9"
        test_user.consent_terms_version = settings.TERMS_VERSION
        db.commit()

        result = PolicyService.check_requires_reconsent(db, test_user)

        assert result.requires_privacy_reconsent is True
        assert result.requires_terms_reconsent is False
        assert result.user_privacy_version == "0.9"

    def test_requires_terms_reconsent_when_version_differs(
        self, db: Session, test_user: User
    ) -> None:
        """Should require terms reconsent when version differs."""
        test_user.consent_privacy_version = settings.PRIVACY_POLICY_VERSION
        test_user.consent_terms_version = "0.9"
        db.commit()

        result = PolicyService.check_requires_reconsent(db, test_user)

        assert result.requires_privacy_reconsent is False
        assert result.requires_terms_reconsent is True
        assert result.user_terms_version == "0.9"


class TestGetPolicyChangelog:
    """Tests for get_policy_changelog."""

    def test_returns_empty_list_when_no_versions(self, db: Session) -> None:
        """Should return empty list when no policy versions exist."""
        result = PolicyService.get_policy_changelog(db, "privacy")

        assert result.policy_type == "privacy"
        assert result.versions == []

    def test_returns_versions_for_policy_type(self, db: Session) -> None:
        """Should return versions for specified policy type."""
        # Create some versions
        v1 = PolicyVersion(
            policy_type="privacy",
            version="1.0",
            effective_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            summary_en="Initial version",
            summary_fr="Version initiale",
        )
        v2 = PolicyVersion(
            policy_type="privacy",
            version="1.1",
            effective_date=datetime(2025, 6, 1, tzinfo=timezone.utc),
            summary_en="Added data portability",
            summary_fr="Ajout de la portabilité des données",
        )
        db.add_all([v1, v2])
        db.commit()

        result = PolicyService.get_policy_changelog(db, "privacy")

        assert len(result.versions) == 2
        # Should be ordered by effective_date desc
        assert result.versions[0].version == "1.1"
        assert result.versions[1].version == "1.0"

    def test_filters_by_since_version(self, db: Session) -> None:
        """Should filter to show only versions after since_version."""
        v1 = PolicyVersion(
            policy_type="terms",
            version="1.0",
            effective_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        v2 = PolicyVersion(
            policy_type="terms",
            version="1.1",
            effective_date=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        v3 = PolicyVersion(
            policy_type="terms",
            version="1.2",
            effective_date=datetime(2025, 12, 1, tzinfo=timezone.utc),
        )
        db.add_all([v1, v2, v3])
        db.commit()

        result = PolicyService.get_policy_changelog(db, "terms", since_version="1.0")

        assert len(result.versions) == 2
        assert all(v.version in ("1.1", "1.2") for v in result.versions)


class TestRecordReconsent:
    """Tests for record_reconsent."""

    def test_updates_privacy_consent(self, db: Session, test_user: User) -> None:
        """Should update privacy consent fields."""
        test_user.consent_privacy_version = "0.9"
        db.commit()

        PolicyService.record_reconsent(
            db=db,
            user=test_user,
            policy_type="privacy",
            ip_address="192.168.1.1",
            user_agent="Test Browser",
        )

        db.refresh(test_user)
        assert test_user.consent_privacy_version == settings.PRIVACY_POLICY_VERSION
        assert test_user.consent_privacy_accepted is True

    def test_updates_terms_consent(self, db: Session, test_user: User) -> None:
        """Should update terms consent fields."""
        test_user.consent_terms_version = "0.9"
        db.commit()

        PolicyService.record_reconsent(
            db=db,
            user=test_user,
            policy_type="terms",
            ip_address="192.168.1.1",
            user_agent="Test Browser",
        )

        db.refresh(test_user)
        assert test_user.consent_terms_version == settings.TERMS_VERSION
        assert test_user.consent_terms_accepted is True

    def test_creates_consent_log(self, db: Session, test_user: User) -> None:
        """Should create a consent log entry."""
        initial_count = (
            db.query(ConsentLog).filter(ConsentLog.user_id == test_user.id).count()
        )

        PolicyService.record_reconsent(
            db=db,
            user=test_user,
            policy_type="privacy",
            ip_address="192.168.1.1",
            user_agent="Test Browser",
        )

        logs = (
            db.query(ConsentLog)
            .filter(
                ConsentLog.user_id == test_user.id,
                ConsentLog.action == "reconsented",
            )
            .all()
        )

        assert len(logs) == initial_count + 1
        log = logs[-1]
        assert log.consent_type == "privacy"
        assert log.ip_address == "192.168.1.1"
        assert log.user_agent == "Test Browser"
