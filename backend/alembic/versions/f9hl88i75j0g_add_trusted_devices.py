"""Add trusted_devices table for 2FA remember device feature

Revision ID: f9hl88i75j0g
Revises: e8gk77h64i9f
Create Date: 2026-01-08

This migration adds the trusted_devices table to support the "Remember This Device"
feature for 2FA authentication. Device tokens are stored as SHA-256 hashes for security,
and IP addresses must be anonymized before storage (Law 25 compliance).

Key security features:
- device_token_hash: SHA-256 hash of device token (never store plaintext)
- ip_address_subnet: Anonymized IP (Law 25 compliance - last octet zeroed)
- consent_logged_at: Timestamp for Law 25 audit trail
- is_active: Soft delete for revocation (retained 7 days then deleted)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f9hl88i75j0g"
down_revision = "e8gk77h64i9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trusted_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "device_token_hash",
            sa.String(64),
            nullable=False,
            unique=True,
            comment="SHA-256 hash of device token (never store plaintext)",
        ),
        sa.Column(
            "device_fingerprint",
            sa.Text(),
            nullable=True,
            comment="JSON blob with device signals (user_agent, ip_subnet, platform_info)",
        ),
        sa.Column(
            "device_name",
            sa.String(100),
            nullable=False,
            comment="User-friendly name (e.g., 'Chrome on Windows')",
        ),
        sa.Column(
            "trusted_at",
            sa.DateTime(),
            nullable=False,
            comment="Timestamp when device was trusted",
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(),
            nullable=True,
            comment="Timestamp of last successful verification",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(),
            nullable=False,
            comment="When trust expires (trusted_at + duration)",
        ),
        sa.Column(
            "ip_address_subnet",
            sa.String(45),
            nullable=True,
            comment="Anonymized IP subnet (Law 25 - must use anonymize_ip())",
        ),
        sa.Column(
            "user_agent",
            sa.String(500),
            nullable=True,
            comment="User agent string when trust was established",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="False if device has been revoked",
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(),
            nullable=True,
            comment="Timestamp when user manually revoked device",
        ),
        sa.Column(
            "consent_logged_at",
            sa.DateTime(),
            nullable=False,
            comment="Timestamp when consent was logged (Law 25 audit trail)",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient queries
    op.create_index(
        "ix_trusted_devices_id",
        "trusted_devices",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_trusted_devices_user_id",
        "trusted_devices",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_trusted_devices_token_hash",
        "trusted_devices",
        ["device_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_trusted_devices_user_active_expires",
        "trusted_devices",
        ["user_id", "is_active", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes first
    op.drop_index(
        "ix_trusted_devices_user_active_expires", table_name="trusted_devices"
    )
    op.drop_index("ix_trusted_devices_token_hash", table_name="trusted_devices")
    op.drop_index("ix_trusted_devices_user_id", table_name="trusted_devices")
    op.drop_index("ix_trusted_devices_id", table_name="trusted_devices")

    # Drop table
    op.drop_table("trusted_devices")
