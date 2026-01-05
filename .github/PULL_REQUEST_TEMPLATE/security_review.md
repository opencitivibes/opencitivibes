## Security Review Checklist

### For reviewers - check before approving:

#### Authentication & Authorization
- [ ] No hardcoded credentials or secrets
- [ ] Proper authentication required on new endpoints
- [ ] Authorization checks for resource access
- [ ] Rate limiting on sensitive endpoints

#### Input Validation
- [ ] All user input sanitized before use
- [ ] SQL queries use ORM or parameterized statements
- [ ] No `dangerouslySetInnerHTML` with user content
- [ ] File uploads validated (type, size, path)

#### Data Protection
- [ ] Sensitive data not logged
- [ ] PII properly handled
- [ ] Appropriate error messages (no stack traces to users)

#### Dependencies
- [ ] New dependencies reviewed for security
- [ ] No known vulnerabilities in added packages

### Automated Checks
- [ ] Bandit scan passed
- [ ] pip-audit passed
- [ ] pnpm audit passed
- [ ] CodeQL analysis passed
