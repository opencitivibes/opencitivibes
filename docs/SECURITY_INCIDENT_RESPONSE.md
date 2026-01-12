# Security Incident Response

## Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| Critical | Active exploitation, data breach | Immediate |
| High | Exploitable vulnerability | 24 hours |
| Medium | Potential vulnerability | 1 week |
| Low | Best practice improvement | Next sprint |

## Response Process

1. **Identify** - Confirm the vulnerability
2. **Contain** - Prevent further exploitation
3. **Eradicate** - Fix the root cause
4. **Recover** - Restore normal operations
5. **Learn** - Document and prevent recurrence

## Vulnerability Classification

### Critical
- Active data exfiltration
- Authentication bypass allowing admin access
- Remote code execution
- SQL injection with data access

### High
- Stored XSS affecting multiple users
- Privilege escalation
- Sensitive data exposure
- Unpatched CVE with public exploit

### Medium
- Reflected XSS
- Information disclosure (non-sensitive)
- Missing security headers
- Outdated dependencies without known exploits

### Low
- Self-XSS
- Missing best practices
- Minor configuration issues

## Incident Handling Steps

### 1. Detection
- Monitor security alerts from CI/CD
- Review security scan reports
- Check for unusual activity in logs
- Respond to responsible disclosure reports

### 2. Triage
- Determine severity level
- Identify affected systems/data
- Document timeline of events
- Notify stakeholders based on severity

### 3. Containment
- Isolate affected systems if needed
- Disable compromised accounts
- Block malicious IPs
- Preserve evidence for analysis

### 4. Remediation
- Develop and test fix
- Review fix for completeness
- Deploy fix to all environments
- Verify fix effectiveness

### 5. Recovery
- Restore normal operations
- Monitor for recurrence
- Reset affected credentials
- Notify affected users if required

### 6. Post-Incident
- Complete incident report
- Update security procedures
- Conduct lessons learned review
- Improve detection capabilities

## Security Scanning Schedule

| Scan Type | Frequency | Tool | Notification |
|-----------|-----------|------|--------------|
| SAST | Every PR | Bandit, CodeQL | PR checks |
| Dependency audit | Every PR + weekly | pip-audit, pnpm audit | PR checks, email |
| Full pentest | Quarterly | Pentest container | Security report |
| Secret scanning | Every commit | detect-secrets | Pre-commit block |

## Contacts

- Security Lead: [Configure in environment]
- On-call: [Configure in environment]
- Disclosure: security@idees-montreal.ca

## Responsible Disclosure

We welcome security researchers to report vulnerabilities responsibly.

### Guidelines
- Do not access data beyond what is needed to demonstrate the issue
- Do not disrupt service availability
- Allow reasonable time for fix before disclosure
- Do not publicly disclose without coordination

### Reporting
- Email: security@idees-montreal.ca
- Include: Description, steps to reproduce, potential impact
- We will acknowledge within 48 hours
- We commit to transparency about fix timeline

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-01 | 1.0.0 | Initial document creation |
