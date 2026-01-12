# Privacy Incident Response Plan

**Version:** 1.0
**Effective Date:** 2026-01-02
**Last Updated:** 2026-01-02

## Overview

This document outlines the procedures for responding to privacy incidents
in compliance with Quebec Law 25 (Act to modernize legislative provisions
as regards the protection of personal information).

## Definitions

**Privacy Incident:** Any event that results in unauthorized access to,
disclosure of, or loss of personal information.

**Breach:** A privacy incident that creates a risk of serious injury to
affected individuals.

**CAI:** Commission d'accès à l'information du Québec - the regulatory
authority for data protection in Quebec.

## Incident Classification

### Severity Levels

| Level | Description | Response Time | CAI Notification |
|-------|-------------|---------------|------------------|
| Critical | Active attack, data exfiltration | Immediate | Required |
| High | Confirmed unauthorized access | 4 hours | Required |
| Medium | Suspicious activity detected | 24 hours | Case-by-case |
| Low | Potential vulnerability | 72 hours | Not required |

### Incident Types

- **unauthorized_access**: Unauthorized access to user data
- **data_loss**: Accidental loss or deletion of data
- **data_breach**: Confirmed data exfiltration or theft
- **system_compromise**: System compromise or malware
- **phishing**: Phishing attack affecting users

## Response Team

### Privacy Officer (Lead)
- Email: privacy@[instance-domain]
- Responsibilities: Overall coordination, CAI communication, user notifications

### Technical Lead
- Responsibilities: Technical investigation, containment, remediation

### Communications Lead
- Responsibilities: User communications, public statements if needed

## Response Procedures

### Phase 1: Detection & Initial Response (0-4 hours)

1. **Identify** the incident
   - Review security alerts (Admin > Security > Alerts)
   - Assess initial scope
   - Document timeline

2. **Contain** the threat
   - Isolate affected systems if needed
   - Revoke compromised credentials
   - Block malicious IPs

3. **Classify** severity
   - Determine incident type
   - Estimate affected users
   - Identify data types involved

4. **Create incident record**
   - Use admin dashboard: Admin > Security > Incidents > Create
   - System auto-generates incident number (INC-YYYY-NNN)
   - Document all actions

### Phase 2: Investigation (4-24 hours)

1. **Collect evidence**
   - Security audit logs (Admin > Security > Audit Logs)
   - System logs
   - Network traffic

2. **Determine scope**
   - Identify all affected users
   - Identify all data types involved
   - Determine attack vector

3. **Root cause analysis**
   - How did the incident occur?
   - What vulnerabilities were exploited?

### Phase 3: Notification (Within 72 hours for serious breaches)

#### CAI Notification (if required)

**When to notify:** If incident creates risk of serious injury to individuals

**How to notify:**
- Online: https://www.cai.gouv.qc.ca/signalement/
- Email: incidents@cai.gouv.qc.ca

**Required information (Article 3.7):**
- [ ] Description of incident
- [ ] Date/period of incident
- [ ] Types of personal information involved
- [ ] Number of affected individuals
- [ ] Measures taken to mitigate risk
- [ ] Contact information

**After notifying:** Record in system (Admin > Security > Incidents > [ID] > Record CAI Notification)

#### User Notification (if required)

**When to notify:** If incident creates risk of serious injury to specific individuals

**How to notify:**
- Direct email to affected users
- Use incident notification templates (auto-generated for FR/EN)

**Required information (Article 3.7):**
- [ ] Description of what happened
- [ ] What data was involved
- [ ] What we are doing about it
- [ ] What they can do to protect themselves
- [ ] Contact information for questions

**After notifying:** Record in system (Admin > Security > Incidents > [ID] > Record User Notification)

### Phase 4: Remediation

1. **Fix vulnerabilities**
   - Patch systems
   - Update configurations
   - Strengthen access controls

2. **Implement preventive measures**
   - Additional monitoring
   - Enhanced authentication
   - Staff training

3. **Update incident record**
   - Document all remediation actions
   - Record lessons learned

### Phase 5: Closure

1. **Verify remediation**
   - Confirm vulnerabilities fixed
   - Test security controls

2. **Final reporting**
   - Complete incident record
   - Update CAI if required

3. **Post-incident review**
   - What went well?
   - What could be improved?
   - Update this plan if needed

## System Features for Incident Management

### Security Audit Logs

Location: Admin > Security > Audit Logs

Logged events include:
- Login successes and failures
- Password changes
- Data exports
- Admin access to PII
- Rate limit violations
- Suspicious activity

### Automated Detection

The system automatically monitors for:
- **Brute force attacks**: >10 failed logins from same IP in 1 hour
- **Mass data exports**: >5 exports by same user in 1 hour
- **Unusual admin access**: >20 PII accesses in 1 hour

Critical alerts automatically:
- Create incident record
- Send notification to admin devices via ntfy

### Incident Register

Location: Admin > Security > Incidents

The incident register tracks:
- Incident number, type, severity, status
- Timeline (discovered, occurred, contained, resolved)
- Affected users and data types
- CAI/user notification status
- Mitigation and preventive measures

## Contact Information

**Privacy Officer:** PRIVACY_OFFICER_EMAIL (configured in platform settings)

**CAI (Commission d'accès à l'information du Québec):**
- Web: https://www.cai.gouv.qc.ca
- Email: incidents@cai.gouv.qc.ca
- Phone: 1-888-528-7741

## Appendix A: Incident Report Template

```
INCIDENT REPORT
===============
Incident Number: INC-YYYY-XXX
Date Discovered: YYYY-MM-DD HH:MM
Date Occurred: YYYY-MM-DD HH:MM (if known)
Severity: [Critical/High/Medium/Low]
Status: [Open/Investigating/Contained/Mitigated/Closed]

DESCRIPTION:
[What happened]

AFFECTED DATA:
- Data types: [email, name, etc.]
- Number of users: [N]

TIMELINE:
[Chronological list of events and actions]

ROOT CAUSE:
[Analysis of how incident occurred]

REMEDIATION:
[Actions taken to fix the issue]

NOTIFICATIONS:
- CAI: [Yes/No] - Date: [YYYY-MM-DD] - Reference: [CAI-XXX]
- Users: [Yes/No] - Date: [YYYY-MM-DD]

LESSONS LEARNED:
[What we learned and will do differently]
```

## Appendix B: Data Types Classification

| Data Type | Sensitivity | CAI Notification if Breached |
|-----------|-------------|------------------------------|
| Email address | Medium | Case-by-case |
| Password hash | High | Likely required |
| Display name | Low | Usually not required |
| IP address | Medium | Case-by-case |
| Idea content | Low | Usually not required |
| Vote history | Low | Usually not required |

## Appendix C: CAI Contact Reference

**Commission d'accès à l'information du Québec**

Mailing Address:
575, rue Saint-Amable, bureau 1.10
Québec (Québec) G1R 2G4

Montreal Office:
500, boulevard René-Lévesque Ouest, bureau 18.200
Montréal (Québec) H2Z 1W7

Website: https://www.cai.gouv.qc.ca
Email: incidents@cai.gouv.qc.ca
Phone: 418-528-7741 / 1-888-528-7741 (toll-free)

---

**Document Control:**
- Version 1.0 created: 2026-01-02
- Next review: 2027-01-02
