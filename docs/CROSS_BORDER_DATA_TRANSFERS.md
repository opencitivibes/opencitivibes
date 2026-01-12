# Cross-Border Data Transfers Documentation

**Version:** 1.0
**Effective Date:** 2026-01-02
**Last Updated:** 2026-01-02

## Overview

This document describes cross-border transfers of personal information
from the IdeesPourMontreal platform, in compliance with Quebec Law 25
Article 17.

## Transfer Inventory

### 1. Sentry (Error Monitoring)

| Attribute | Details |
|-----------|---------|
| Recipient | Sentry (Functional Software Inc.) |
| Location | United States |
| Website | https://sentry.io |
| Data Transferred | Error logs, stack traces, correlation IDs, user IDs |
| NOT Transferred | Email addresses, passwords, usernames, personal content |
| Purpose | Application error monitoring and debugging |
| Legal Basis | Legitimate interest (platform stability) |

**Safeguards:**
- Data Processing Agreement (DPA) in place
- EU Standard Contractual Clauses (SCCs) apply
- SOC 2 Type II certified
- PII scrubbing implemented before data sent
- User IDs only (no direct PII)

**DPA Link:** https://sentry.io/legal/dpa/

**Risk Assessment:** Low - No direct PII transferred; technical data only.

### 2. Email Service Provider

| Attribute | Details |
|-----------|---------|
| Recipient | Configured per instance (SMTP) |
| Location | Varies by configuration |
| Data Transferred | Email addresses, email content (login codes, notifications) |
| Purpose | Transactional email delivery |
| Legal Basis | Contract (service delivery), Consent (notifications) |

**Safeguards:**
- TLS encryption for all email transmission
- Data Processing Agreement with provider
- No email content stored beyond delivery
- Transactional emails only (no marketing without consent)

**Risk Assessment:** Low-Medium - Email addresses necessary for service.

### 3. Hosting Infrastructure

| Attribute | Details |
|-----------|---------|
| Provider | To be specified per deployment |
| Location | Canada preferred (Toronto/Montreal) |
| Data Stored | All application data |
| Purpose | Application hosting |
| Legal Basis | Contract (service operation) |

**Safeguards:**
- Encryption at rest (database, files)
- Encryption in transit (TLS)
- Physical security (data center)
- Access controls
- Regular security audits

**Recommendation:** Prioritize Canadian hosting (e.g., DigitalOcean Toronto,
OVH Montreal) to minimize cross-border transfers.

## Transfer Impact Assessment

### Adequacy Determination

| Jurisdiction | Adequacy Status | Additional Safeguards |
|--------------|-----------------|----------------------|
| Canada | Adequate | Standard measures |
| European Union | Adequate | Standard measures |
| United States | Not adequate | SCCs, DPA, PII minimization |

### Risk Mitigation

For transfers to United States (Sentry):

1. **PII Minimization:** Email addresses, passwords, and personal content
   are never sent to Sentry. Only technical error data with anonymized
   user IDs.

2. **Contractual Safeguards:** Standard Contractual Clauses (SCCs) provide
   legal protection equivalent to Law 25.

3. **Technical Safeguards:** Before-send PII scrubbing removes any
   accidentally included personal information.

4. **Monitoring:** Regular review of data sent to Sentry.

## User Rights

Users may request information about cross-border transfers by contacting:
- Email: privacy@idees-montreal.ca
- Subject: "Cross-Border Transfer Information Request"

## Updates

This document is reviewed and updated:
- When new third-party services are added
- When existing service providers change locations
- Annually as part of compliance review

## Contact

Privacy Officer: privacy@idees-montreal.ca
