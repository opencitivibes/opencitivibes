import os
import sys
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _should_load_env_file() -> str | None:
    """Determine if .env should be loaded.

    For local development, load `.env` automatically so `SECRET_KEY` can be
    provided from `backend/.env` (convenience). **SECRET_KEY remains required**
    and must be set in production via environment variables.

    Do NOT auto-load `.env` when running under pytest or in CI (so tests
    that validate missing secrets continue to fail fast).
    """
    if any("pytest" in str(x) for x in sys.argv if x):
        return None
    if os.environ.get("CI") in ("1", "true", "True"):
        return None
    return ".env"


class Settings(BaseSettings):
    # Environment configuration
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment: 'development', 'staging', or 'production'",
    )

    DATABASE_URL: str = "sqlite:///./data/opencitivibes.db"
    SECRET_KEY: str = Field(
        ...,  # Required, no default
        description="JWT secret key - must be set via SECRET_KEY environment variable",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins (comma-separated in env var)",
    )

    # Admin credentials for initial setup (used by init_db.py)
    # These MUST be set via environment variables - no defaults for security
    # In development, set these in backend/.env
    # In production, set via secure environment variable injection
    ADMIN_EMAIL: str = Field(
        ...,  # Required, no default
        description="Admin email - must be set via ADMIN_EMAIL environment variable",
    )
    ADMIN_PASSWORD: str = Field(
        ...,  # Required, no default
        description="Admin password - must be set via ADMIN_PASSWORD environment variable",
    )

    # Database connection pool settings
    DB_POOL_SIZE: int = Field(
        default=5,
        description="Number of persistent connections in pool",
    )
    DB_MAX_OVERFLOW: int = Field(
        default=10,
        description="Extra connections when pool exhausted",
    )
    DB_POOL_TIMEOUT: int = Field(
        default=30,
        description="Seconds to wait for connection from pool",
    )
    DB_POOL_RECYCLE: int = Field(
        default=1800,
        description="Recycle connections after N seconds (30 min default)",
    )

    # Safety: avoid creating DB schema automatically unless explicitly enabled.
    AUTO_CREATE_DB: bool = Field(
        default=False,
        description="When true (development only), call Base.metadata.create_all on startup",
    )

    # Performance settings
    SLOW_REQUEST_THRESHOLD: float = Field(
        default=1.0,
        description="Log warning for requests slower than this (seconds)",
    )

    # Search configuration
    SEARCH_BACKEND: str | None = Field(
        default=None,
        description="Search backend: 'sqlite_fts5' or 'postgresql_fts'. Auto-detect if None.",
    )
    SEARCH_MIN_QUERY_LENGTH: int = Field(
        default=2,
        description="Minimum query length for search",
    )
    SEARCH_MAX_RESULTS: int = Field(
        default=100,
        description="Maximum results per search query",
    )
    SEARCH_DEFAULT_LIMIT: int = Field(
        default=20,
        description="Default number of results per page",
    )

    # Platform configuration path (for OpenCitiVibes multi-instance support)
    PLATFORM_CONFIG_PATH: str = Field(
        default="./config/platform.config.json",
        description="Path to platform configuration file for instance customization.",
    )

    # Phase 3: Relevance tuning settings
    SEARCH_WEIGHT_TITLE: float = Field(
        default=1.0,
        description="Weight for title matches in relevance scoring",
    )
    SEARCH_WEIGHT_DESCRIPTION: float = Field(
        default=0.6,
        description="Weight for description matches in relevance scoring",
    )
    SEARCH_WEIGHT_TAGS: float = Field(
        default=0.8,
        description="Weight for tag matches in relevance scoring",
    )
    SEARCH_FRESHNESS_BOOST: float = Field(
        default=0.1,
        description="Boost factor for recent ideas (0-1 range)",
    )
    SEARCH_POPULARITY_BOOST: float = Field(
        default=0.05,
        description="Boost per vote in relevance scoring",
    )
    SEARCH_MAX_POPULARITY_BOOST: float = Field(
        default=0.2,
        description="Maximum popularity boost cap",
    )

    # Email Login Settings
    EMAIL_LOGIN_CODE_EXPIRY_MINUTES: int = Field(
        default=10,
        description="Minutes until email login code expires",
    )
    EMAIL_LOGIN_MAX_ATTEMPTS: int = Field(
        default=5,
        description="Maximum verification attempts per code",
    )
    EMAIL_LOGIN_CODES_PER_HOUR: int = Field(
        default=3,
        description="Maximum login codes per email per hour",
    )
    EMAIL_LOGIN_CODE_LENGTH: int = Field(
        default=6,
        description="Number of digits in login code",
    )

    # Email Provider Settings
    EMAIL_PROVIDER: str = Field(
        default="console",
        description="Email provider: 'smtp', 'sendgrid', 'ses', 'console'",
    )
    SMTP_HOST: str = Field(
        default="localhost",
        description="SMTP server hostname",
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP server port",
    )
    SMTP_USER: str = Field(
        default="",
        description="SMTP username",
    )
    SMTP_PASSWORD: str = Field(
        default="",
        description="SMTP password",
    )
    SMTP_FROM_EMAIL: str = Field(
        default="noreply@opencitivibes.app",
        description="From email address",
    )
    SMTP_FROM_NAME: str = Field(
        default="OpenCitiVibes",
        description="From display name",
    )
    SMTP_USE_TLS: bool = Field(
        default=True,
        description="Use STARTTLS for SMTP connection (port 587)",
    )
    SMTP_USE_SSL: bool = Field(
        default=False,
        description="Use implicit SSL for SMTP connection (port 465)",
    )

    # SendGrid (alternative provider)
    SENDGRID_API_KEY: str = Field(
        default="",
        description="SendGrid API key (if using SendGrid provider)",
    )

    # 2FA (TOTP) Settings
    TOTP_ENCRYPTION_KEY: str = Field(
        default="",
        description="Fernet key for encrypting TOTP secrets at rest. Generate with: "
        'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"',
    )
    TOTP_ISSUER_NAME: str = Field(
        default="OpenCitiVibes",
        description="Issuer name shown in authenticator apps",
    )
    TOTP_TEMP_TOKEN_EXPIRE_MINUTES: int = Field(
        default=5,
        description="Minutes until 2FA temp token expires",
    )
    TOTP_BACKUP_CODE_COUNT: int = Field(
        default=10,
        description="Number of backup codes to generate",
    )

    # 2FA Trusted Device Settings (Remember Device Feature - Law 25 Compliance)
    TOTP_DEVICE_TRUST_DEFAULT_DAYS: int = Field(
        default=30,
        description="Default duration for device trust in days",
    )
    TOTP_DEVICE_TRUST_MAX_DAYS: int = Field(
        default=30,
        description="Maximum allowed trust duration in days (MUST NOT exceed 30 - Law 25)",
    )
    TOTP_DEVICE_TOKEN_LENGTH: int = Field(
        default=32,
        description="Length of device token in bytes (32 bytes = 256 bits)",
    )
    TOTP_MAX_TRUSTED_DEVICES_PER_USER: int = Field(
        default=10,
        description="Maximum number of trusted devices per user (prevent abuse)",
    )
    TOTP_REVOKED_DEVICE_RETENTION_DAYS: int = Field(
        default=7,
        description="Days to retain revoked devices before permanent deletion (Law 25)",
    )

    # Legal Document Versions (Law 25 Compliance)
    TERMS_VERSION: str = Field(
        default="1.0",
        description="Current version of Terms of Service",
    )
    PRIVACY_POLICY_VERSION: str = Field(
        default="1.0",
        description="Current version of Privacy Policy",
    )
    PRIVACY_OFFICER_EMAIL: str = Field(
        default="privacy@opencitivibes.app",
        description="Privacy officer email for breach notifications",
    )
    PRIVACY_OFFICER_NAME: str = Field(
        default="Privacy Officer",
        description="Privacy officer name for breach notifications",
    )
    PROJECT_NAME: str = Field(
        default="OpenCitiVibes",
        description="Project name for notifications and branding",
    )

    # Security Monitoring Thresholds (Law 25 Article 3.5)
    SECURITY_BRUTE_FORCE_THRESHOLD: int = Field(
        default=10,
        description="Failed login attempts from same IP before alert (per hour)",
    )
    SECURITY_MASS_EXPORT_THRESHOLD: int = Field(
        default=5,
        description="Data exports by same user before alert (per hour)",
    )
    SECURITY_ADMIN_ACCESS_THRESHOLD: int = Field(
        default=20,
        description="Admin PII accesses before alert (per hour)",
    )

    # Data Retention Settings (Law 25 Compliance - Phase 3)
    SOFT_DELETE_RETENTION_DAYS: int = Field(
        default=30,
        description="Days to keep soft-deleted content before permanent deletion",
    )
    INACTIVE_ACCOUNT_RETENTION_YEARS: int = Field(
        default=3,
        description="Years of inactivity before account anonymization warning",
    )
    INACTIVE_ACCOUNT_GRACE_PERIOD_DAYS: int = Field(
        default=30,
        description="Days after warning before account anonymization",
    )
    EXPIRED_LOGIN_CODE_RETENTION_DAYS: int = Field(
        default=7,
        description="Days to keep expired email login codes for audit",
    )
    EXPIRED_TOTP_TOKEN_RETENTION_HOURS: int = Field(
        default=24,
        description="Hours to keep expired 2FA temporary tokens",
    )
    CONSENT_LOG_RETENTION_YEARS: int = Field(
        default=7,
        description="Years to keep consent logs for compliance audit",
    )
    SECURITY_AUDIT_LOG_RETENTION_YEARS: int = Field(
        default=5,
        description="Years to keep security audit logs",
    )

    # Ntfy Push Notification Settings
    NTFY_URL: str = Field(
        default="",
        description="Ntfy server URL (internal Docker: http://ntfy:80)",
    )
    NTFY_TOPIC_PREFIX: str = Field(
        default="idees-admin",
        description="Prefix for notification topics",
    )
    NTFY_AUTH_TOKEN: str = Field(
        default="",
        description="Optional auth token for publishing (if ntfy requires auth)",
    )
    NTFY_ENABLED: bool = Field(
        default=True,
        description="Enable/disable notifications globally",
    )
    APP_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend URL for notification deep links",
    )

    # Beta Access Settings (Security Hardening Phase 1)
    BETA_MODE: bool = Field(
        default=False,
        description="Enable beta mode - requires password to access site",
    )
    BETA_PASSWORD: str = Field(
        default="",
        description="Beta access password (server-side only, never exposed to client)",
    )

    def get_search_backend(self) -> str:
        """Determine search backend from config or DATABASE_URL."""
        if self.SEARCH_BACKEND:
            return self.SEARCH_BACKEND
        if self.DATABASE_URL.startswith("postgresql"):
            return "postgresql_fts"
        return "sqlite_fts5"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = SettingsConfigDict(
        env_file=_should_load_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",  # Allow extra env vars (e.g., SENTRY_DSN) without validation errors
    )


# Rely on pydantic BaseSettings to load `.env` and validate required fields.
# Instantiating Settings() will raise pydantic.ValidationError if SECRET_KEY isn't set (including when absent from `.env`).
settings = Settings()  # type: ignore[call-arg]


def get_settings() -> Settings:
    """Get the settings instance (for dependency injection)."""
    return settings
