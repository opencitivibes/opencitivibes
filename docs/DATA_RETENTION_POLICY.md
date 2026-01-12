# Data Retention Policy

**Effective Date:** 2026-01-02
**Last Updated:** 2026-01-02
**Version:** 1.0

## Overview

This document outlines the data retention policies for the OpenCitiVibes platform
in compliance with Quebec Law 25 (Loi 25).

## Legal Basis

- **Article 11:** Personal information must be destroyed when no longer necessary for the purposes collected
- **Article 12:** Organizations must have documented retention schedules
- **Article 13:** When retention period expires, information must be destroyed or anonymized

## Retention Periods

### User Account Data

| Data Type | Retention Period | Action After Expiry |
|-----------|------------------|---------------------|
| Active account | Indefinite while active | N/A |
| Inactive account | 3 years of inactivity | Anonymization |
| Deleted account | 30 days | Permanent anonymization |

### User Content

| Data Type | Retention Period | Action After Expiry |
|-----------|------------------|---------------------|
| Published ideas | Indefinite (unless deleted) | N/A |
| Soft-deleted ideas | 30 days | Permanent deletion |
| Comments | Indefinite (unless deleted) | N/A |
| Soft-deleted comments | 30 days | Permanent deletion |
| Votes | Indefinite (tied to account) | Deleted with account |

### Authentication Data

| Data Type | Retention Period | Action After Expiry |
|-----------|------------------|---------------------|
| Email login codes | 7 days after expiry | Permanent deletion |
| 2FA backup codes | Tied to account | Deleted with account |
| Password hashes | Tied to account | Cleared on anonymization |

### Audit & Compliance Data

| Data Type | Retention Period | Action After Expiry |
|-----------|------------------|---------------------|
| Consent logs | 7 years | Deletion for anonymized users |
| Security audit logs | 5 years | Permanent deletion |
| Moderation logs | 5 years | Permanent deletion |

## Automated Cleanup Process

### Daily Cleanup Job (2:00 AM)

1. **Soft-deleted content cleanup**
   - Permanently deletes ideas/comments soft-deleted >30 days ago

2. **Expired authentication cleanup**
   - Deletes expired email login codes (>7 days old)

3. **Inactive account processing**
   - Sends warning to accounts inactive >3 years
   - Anonymizes accounts 30 days after warning (if still inactive)

### Manual Cleanup

Administrators can trigger manual cleanup via the admin dashboard
when immediate cleanup is required.

**Admin Endpoints:**
- `GET /api/admin/retention/status` - View retention metrics
- `POST /api/admin/retention/run-cleanup` - Trigger manual cleanup
- `GET /api/admin/retention/scheduler` - Check scheduler status

## User Rights

### Right to Deletion

Users can request account deletion at any time via:
- Self-service: Settings > Delete Account
- Email: privacy@opencitivibes.app

Deletion is processed immediately upon confirmation.

### Right to Data Export

Users can export their data at any time via:
- Self-service: Settings > My Data > Download

## Exceptions

Data may be retained beyond standard periods for:
- Legal hold orders
- Ongoing investigations
- Regulatory requirements

## Configuration

Retention periods are configurable via environment variables:

```
SOFT_DELETE_RETENTION_DAYS=30
INACTIVE_ACCOUNT_RETENTION_YEARS=3
INACTIVE_ACCOUNT_GRACE_PERIOD_DAYS=30
EXPIRED_LOGIN_CODE_RETENTION_DAYS=7
CONSENT_LOG_RETENTION_YEARS=7
SECURITY_AUDIT_LOG_RETENTION_YEARS=5
```

## Contact

For questions about data retention:
- Privacy Officer: privacy@opencitivibes.app
- Commission d'accès à l'information: https://www.cai.gouv.qc.ca
