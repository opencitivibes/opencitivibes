# Integration Tests

This directory contains comprehensive integration tests for the backend API, focusing on end-to-end flows that test the complete request-response cycle.

## Test Files

### test_password_reset_integration.py
**Status:** ✅ All 20 tests passing

Comprehensive tests for the password reset flow:

**Test Coverage:**
- **Complete Flow**: Test the entire password reset process (request → verify → reset → login)
- **Request Endpoint**: Valid/invalid emails, email enumeration prevention, case-insensitivity
- **Verify Endpoint**: Valid/invalid codes, max attempts, expired codes
- **Reset Endpoint**: Valid/weak passwords, common passwords, breached passwords, token validation
- **Security Features**: Session invalidation, single-use tokens, timing attack protection

**Bugs Caught:**
- Import errors (correct function names)
- Password validation requirements (sequential numbers, repeated characters)
- Security edge cases

**Key Tests:**
```python
def test_complete_password_reset_flow()  # Full E2E test
def test_timing_attack_protection()      # Security validation
def test_session_invalidation_after_reset()  # Token version implementation
```

### test_2fa_integration.py
**Status:** ⚠️ 16/24 tests need API fixes

Comprehensive tests for 2FA (TOTP) flows:

**Test Coverage:**
- **Setup Flow**: Initialize 2FA, verify setup, generate backup codes
- **Login Flow**: 2FA required login, backup code usage, invalid codes
- **Disable Flow**: Disable with password, error cases
- **Backup Codes**: Regenerate codes, view count
- **Trusted Devices**: Trust device during login, list/revoke devices
- **Security Features**: Authentication requirements, consent validation

**Bugs Caught:**
- Missing model attributes (`get_verified_totp`)
- Import errors (`decrypt_totp_secret`)
- API endpoint issues (DELETE with json body)
- Missing TOTP_ENCRYPTION_KEY in test environment

**Fixes Needed:**
1. Fix `get_verified_totp` method or use correct repository method
2. Import `decrypt_totp_secret` correctly or use repository method
3. Use `data` instead of `json` for DELETE requests in TestClient
4. Update test assertions for actual API response formats

### test_auth_integration.py
**Status:** ⚠️ Basic auth tests (auto-generated)

Basic authentication tests that need updates:
- Registration flow
- Login flow
- Consent management
- Activity history

## Running Tests

```bash
# All integration tests
cd backend
uv run pytest tests/test_integration/ -v

# Specific test file
uv run pytest tests/test_integration/test_password_reset_integration.py -v

# Single test
uv run pytest tests/test_integration/test_password_reset_integration.py::TestPasswordResetFullFlow::test_complete_password_reset_flow -v

# With detailed output
uv run pytest tests/test_integration/test_password_reset_integration.py -v --tb=short
```

## Test Environment

Tests use:
- In-memory SQLite database (fresh for each test)
- Mocked email service
- Rate limiter reset between tests
- Test-specific environment variables (see `conftest.py`)

**Required Environment Variables (set in conftest.py):**
- `SECRET_KEY`: JWT signing key
- `TOTP_ENCRYPTION_KEY`: Fernet key for 2FA secret encryption
- `ADMIN_EMAIL`, `ADMIN_PASSWORD`: Admin credentials

## Fixtures

Common fixtures available (from `conftest.py`):

### Database
- `db_session` / `db`: Fresh database session
- `client`: TestClient with database dependency override

### Users
- `test_user`: Standard user with consent
- `admin_user`: Global admin user
- `password_reset_user`: User for password reset tests
- `user_for_2fa`: User for 2FA setup tests
- `user_with_2fa_enabled`: User with 2FA already configured

### Auth
- `auth_headers`: Bearer token for test_user
- `admin_auth_headers`: Bearer token for admin_user

### Test Data
- `test_category`: Sample category
- `test_idea`: Approved idea
- `pending_idea`: Pending idea

## Test Patterns

### Integration Test Structure
```python
class TestFeatureFlow:
    """Test complete feature flow."""

    def test_complete_flow(self, client, db_session, user_fixture):
        """
        Test end-to-end flow.

        Validates:
        - Step 1 works
        - Step 2 works
        - Final state is correct
        """
        # Step 1: Initial action
        response = client.post("/api/endpoint", json={...})
        assert response.status_code == 200

        # Step 2: Follow-up action
        data = response.json()
        response = client.post("/api/next", json={...})
        assert response.status_code == 200

        # Verify final state
        db_session.refresh(user_fixture)
        assert user_fixture.attribute == expected_value
```

### Testing Error Cases
```python
def test_error_case(self, client):
    """Test that invalid input is rejected."""
    response = client.post("/api/endpoint", json={"invalid": "data"})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "expected error message" in detail.lower()
```

### Security Testing
```python
def test_security_feature(self, client):
    """Test security measure."""
    # Test that security control is enforced
    response = client.get("/api/protected")
    assert response.status_code == 401  # Unauthorized
```

## Best Practices

1. **Test Complete Flows**: Each test file should have at least one end-to-end test
2. **Independent Tests**: Each test should be self-contained and not depend on others
3. **Clear Docstrings**: Explain what each test validates
4. **Descriptive Names**: Test names should clearly indicate what is being tested
5. **Error Cases**: Test both success and failure paths
6. **Security**: Include tests for authentication, authorization, and security features
7. **Real API Calls**: Use TestClient to make actual HTTP requests
8. **Mock External Services**: Mock email, external APIs, etc.

## Benefits of Integration Tests

These tests catch issues that unit tests miss:

1. **Import Errors**: Incorrect function/class names
2. **Model Attributes**: Missing or renamed database columns
3. **API Contract**: Endpoint paths, request/response formats
4. **Flow Logic**: Multi-step processes that must work together
5. **Security**: Authentication, authorization, data validation
6. **Edge Cases**: Concurrent requests, race conditions, timing issues

## Future Enhancements

- [ ] Fix remaining 2FA test issues
- [ ] Add tests for email verification flow
- [ ] Add tests for admin moderation flow
- [ ] Add tests for voting and commenting flows
- [ ] Add performance tests (rate limiting, concurrent requests)
- [ ] Add tests for data export/deletion (Law 25 compliance)
