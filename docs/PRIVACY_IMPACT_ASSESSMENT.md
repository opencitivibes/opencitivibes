# Privacy Impact Assessment (PIA)
## IdeesPourMontreal Civic Engagement Platform

**Document Version:** 1.0
**Assessment Date:** 2026-01-02
**Assessor:** Privacy Officer
**Next Review Date:** 2027-01-02

---

## 1. Project Overview

### 1.1 Purpose

This Privacy Impact Assessment evaluates the privacy risks associated with
the IdeesPourMontreal civic engagement platform, in compliance with Quebec
Law 25 (Loi 25).

### 1.2 Platform Description

IdeesPourMontreal is a web-based platform enabling citizens to:
- Submit ideas for civic improvements
- Vote on submitted ideas
- Comment on and discuss ideas
- Participate in community engagement

### 1.3 Legal Basis

Processing is based on:
- **Consent:** Explicit consent obtained at registration
- **Legitimate Interest:** Civic engagement and community benefit
- **Contract:** Provision of platform services

---

## 2. Personal Information Inventory

### 2.1 Data Collected

| Category | Data Elements | Purpose | Retention |
|----------|--------------|---------|-----------|
| Account | Email, username, display name | User identification | Account lifetime + 30 days |
| Authentication | Password hash, 2FA secrets | Security | Account lifetime |
| Profile | Avatar, bio, official status | User profile display | Account lifetime |
| Content | Ideas, comments | Civic engagement | Indefinite (soft-delete 30 days) |
| Votes | Vote records, qualities | Idea ranking | Account lifetime |
| Consent | Consent records, timestamps | Compliance | 7 years |
| Technical | IP addresses (login codes only) | Security | 7 days |
| Audit | Security logs | Breach detection | 5 years |

### 2.2 Data Sources

- **Direct from users:** Registration, profile updates, content submission
- **Automatically collected:** IP addresses (limited), timestamps
- **Third parties:** None

### 2.3 Data Recipients

| Recipient | Data Shared | Purpose | Safeguards |
|-----------|------------|---------|------------|
| Sentry | Error logs, user IDs | Error monitoring | DPA, SCCs, PII scrubbing |
| Email Provider | Email addresses | Transactional emails | TLS, DPA |
| Hosting Provider | All data | Infrastructure | Encryption, DPA |

---

## 3. Risk Assessment

### 3.1 Risk Identification

| # | Risk | Description | Likelihood | Impact |
|---|------|-------------|------------|--------|
| R1 | Unauthorized access | Attacker gains access to user data | Medium | High |
| R2 | Data breach | User data exposed publicly | Low | High |
| R3 | Identity disclosure | Users identified on sensitive topics | Medium | Medium |
| R4 | Harassment | Users targeted based on civic opinions | Medium | Medium |
| R5 | Insider threat | Admin misuses access to PII | Low | High |
| R6 | Data loss | Data permanently lost | Low | Medium |
| R7 | Cross-border exposure | Data inadequately protected abroad | Low | Medium |

### 3.2 Risk Analysis

#### R1: Unauthorized Access

**Current Controls:**
- Bcrypt password hashing
- JWT with short expiry (30 min)
- Optional 2FA (TOTP)
- Rate limiting on authentication
- Account lockout after failed attempts

**Residual Risk:** Low

**Additional Measures:** None required

#### R2: Data Breach

**Current Controls:**
- HTTPS/TLS in transit
- Database access restricted
- Security audit logging
- Breach detection monitoring
- Incident response plan

**Residual Risk:** Low

**Additional Measures:** None required

#### R3: Identity Disclosure

**Current Controls:**
- Pseudonymous participation available
- Display name separate from username
- Privacy settings for profile visibility
- No requirement to use real name

**Residual Risk:** Low (user choice)

**Additional Measures:**
- Educate users about privacy settings
- Default to more private settings (consider)

#### R4: Harassment

**Current Controls:**
- Content moderation system
- Flag/report functionality
- Trust score system
- Admin review of flagged content
- User blocking (if implemented)

**Residual Risk:** Medium

**Additional Measures:**
- Consider anonymous voting option
- Implement user blocking feature

#### R5: Insider Threat

**Current Controls:**
- Role-based access control
- Security audit logging
- Admin action logging
- Least privilege principle

**Residual Risk:** Low

**Additional Measures:**
- Implement admin access alerts for PII
- Regular access review

#### R6: Data Loss

**Current Controls:**
- Database backups
- Soft-delete with recovery period
- User data export functionality

**Residual Risk:** Low

**Additional Measures:** None required

#### R7: Cross-Border Exposure

**Current Controls:**
- DPAs with service providers
- PII scrubbing for Sentry
- Canadian hosting (if applicable)
- Documented transfers

**Residual Risk:** Low

**Additional Measures:** None required

---

## 4. Privacy Principles Compliance

### 4.1 Lawfulness, Fairness, Transparency

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Legal basis documented | Compliant | Privacy policy section 4 |
| Clear privacy policy | Compliant | FR/EN versions available |
| Consent obtained | Compliant | Registration checkboxes |
| Purpose clearly stated | Compliant | Privacy policy section 3 |

### 4.2 Purpose Limitation

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Purposes specified | Compliant | Privacy policy section 3 |
| No incompatible use | Compliant | Data used only for civic engagement |
| Marketing opt-in only | Compliant | Separate consent checkbox |

### 4.3 Data Minimization

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Only necessary data | Compliant | Minimal registration fields |
| Optional fields marked | Compliant | Avatar, bio optional |
| No excessive collection | Compliant | No tracking cookies |

### 4.4 Accuracy

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Users can correct data | Compliant | Profile update endpoint |
| Inaccurate data handled | Compliant | Email change requires verification |

### 4.5 Storage Limitation

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Retention periods defined | Compliant | Data retention policy |
| Automated cleanup | Compliant | Scheduled retention jobs |
| Inactive account handling | Compliant | 3-year inactivity policy |

### 4.6 Security

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Encryption in transit | Compliant | HTTPS/TLS |
| Password security | Compliant | Bcrypt hashing |
| Access controls | Compliant | RBAC implementation |
| Breach detection | Compliant | Security monitoring |

### 4.7 Accountability

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PIA conducted | Compliant | This document |
| Consent records | Compliant | ConsentLog table |
| Audit trails | Compliant | SecurityAuditLog table |
| Privacy officer | Compliant | Designated in config |

---

## 5. Data Subject Rights

| Right | Implemented | Method |
|-------|------------|--------|
| Access | Yes | GET /api/auth/export-data |
| Rectification | Yes | PUT /api/auth/profile |
| Erasure | Yes | DELETE /api/auth/account |
| Portability | Yes | GET /api/auth/export-data (JSON/CSV) |
| Object | Yes | Consent management |
| Consent withdrawal | Yes | PUT /api/auth/consent |

---

## 6. Third-Party Processing

### 6.1 Sentry (Error Monitoring)

- **Location:** United States
- **Data Transferred:** Error logs, correlation IDs, user IDs (no PII)
- **Safeguards:** SOC 2 Type II, DPA, Standard Contractual Clauses
- **PII Minimization:** Email/password never sent; user IDs only
- **Risk Level:** Low

### 6.2 Email Service Provider

- **Provider:** SMTP configured per instance
- **Location:** Varies by configuration
- **Data Transferred:** Email addresses, email content
- **Safeguards:** TLS encryption, DPA
- **Purpose:** Transactional emails only
- **Risk Level:** Low

### 6.3 Hosting Provider

- **Provider:** To be specified per deployment
- **Location:** Canada preferred
- **Data Transferred:** All application data
- **Safeguards:** Encryption at rest/in transit, physical security, DPA
- **Risk Level:** Low (if Canadian) / Medium (if non-Canadian)

---

## 7. Recommendations

### 7.1 Implemented (This Assessment)

1. Explicit consent at registration
2. Data export functionality
3. Self-service account deletion
4. Privacy settings for profiles
5. Security audit logging
6. Breach detection and response
7. Data retention automation

### 7.2 Future Considerations

1. **Anonymous Voting:** Consider allowing anonymous votes to reduce
   harassment risk for controversial topics

2. **User Blocking:** Implement user-to-user blocking feature

3. **Enhanced Privacy Defaults:** Consider defaulting new users to
   "registered" visibility rather than "public"

4. **Local Hosting:** Prioritize Canadian hosting providers to
   minimize cross-border transfer risks

---

## 8. Conclusion

This assessment concludes that the IdeesPourMontreal platform, with the
implemented privacy controls, presents **acceptable privacy risk** for
users. The platform:

- Collects only necessary personal information
- Provides robust security controls
- Enables user control over personal data
- Has clear retention policies
- Meets Law 25 requirements for data subject rights
- Has adequate breach detection and response capabilities

The residual risks are proportionate to the public benefit of civic
engagement facilitated by the platform.

---

## 9. Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Privacy Officer | _____________ | _____________ | _______ |
| Technical Lead | _____________ | _____________ | _______ |
| Project Owner | _____________ | _____________ | _______ |

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-02 | Privacy Officer | Initial assessment |

---

## Appendix A: Data Flow Diagram

```
[User] --> [Frontend (Next.js)]
              |
              | HTTPS
              v
        [Backend (FastAPI)]
              |
       +------+------+
       |             |
       v             v
  [Database]    [Sentry]
  (SQLite/     (Error
   PostgreSQL)  Monitoring)
       |
       v
  [Email Service]
  (Transactional
   emails)
```

## Appendix B: Referenced Documents

- Privacy Policy: /privacy
- Terms of Service: /terms
- Data Retention Policy: docs/DATA_RETENTION_POLICY.md
- Incident Response Plan: docs/INCIDENT_RESPONSE_PLAN.md
- Cross-Border Transfers: docs/CROSS_BORDER_DATA_TRANSFERS.md
