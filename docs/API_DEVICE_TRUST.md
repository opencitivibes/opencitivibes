# Device Trust API Documentation

## Overview

The Device Trust feature allows users to bypass TOTP two-factor authentication on trusted devices. This enhances user experience while maintaining security by:

- **Requiring password authentication** - Device trust ONLY bypasses TOTP code entry
- **Explicit consent** - Users must explicitly consent to device trust (Law 25 compliance)
- **Time-limited trust** - Maximum 30 days, configurable by user
- **Full transparency** - Users can view and revoke all trusted devices

## Law 25 Compliance

This feature complies with Quebec's Law 25 (Protection of Personal Information):

| Requirement | Implementation |
|------------|----------------|
| Explicit Consent (Art. 8.1) | `consent_given=true` required |
| Right to Access (Art. 27) | List devices endpoint |
| Right to Withdraw (Art. 9.1) | Revoke device endpoints |
| Data Minimization | IP anonymized to subnet |
| Transparency | Email notification on trust |
| Retention Limits | Auto-delete after 30 days max |

## Authentication Flow

### Standard 2FA Login (No Device Trust)

```
1. POST /auth/login → TwoFactorRequiredResponse
2. POST /auth/2fa/verify → Token
```

### Login with Trusted Device

```
1. POST /auth/login + X-Device-Token header → Token (skips TOTP)
```

### Trust a New Device

```
1. POST /auth/login → TwoFactorRequiredResponse
2. POST /auth/2fa/verify + trust_device=true → Token + device_token
```

## Endpoints

### POST /auth/2fa/verify

Complete 2FA verification with optional device trust.

**Request:**
```json
{
  "temp_token": "eyJhbGciOiJIUzI1...",
  "code": "123456",
  "is_backup_code": false,
  "trust_device": true,
  "trust_duration_days": 30,
  "consent_given": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `temp_token` | string | Yes | Temporary token from login response |
| `code` | string | Yes | 6-digit TOTP code or 8-char backup code |
| `is_backup_code` | boolean | No | True if using backup code |
| `trust_device` | boolean | No | True to remember this device |
| `trust_duration_days` | integer | No | Days to trust (1-30, default: 30) |
| `consent_given` | boolean | **Yes if trust_device=true** | Explicit consent for Law 25 |

**Response (with device trust):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer",
  "device_token": "abc123xyz...",
  "device_expires_at": "2025-02-07T12:00:00Z"
}
```

**Response (without device trust):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer"
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 400 | `trust_device=true` without `consent_given=true` |
| 400 | `trust_duration_days` > 30 |
| 400 | Invalid or expired temp_token |
| 401 | Invalid TOTP code |
| 429 | Rate limit exceeded (10/minute) |

---

### GET /auth/2fa/devices

List all trusted devices for the authenticated user.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "devices": [
    {
      "id": 123,
      "device_name": "Chrome on Windows 10",
      "trusted_at": "2025-01-08T12:00:00Z",
      "expires_at": "2025-02-07T12:00:00Z",
      "last_used_at": "2025-01-10T15:30:00Z",
      "is_active": true
    }
  ],
  "total": 1
}
```

---

### PATCH /auth/2fa/devices/{device_id}

Rename a trusted device.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "device_name": "My Home Computer"
}
```

**Response:**
```json
{
  "id": 123,
  "device_name": "My Home Computer",
  "trusted_at": "2025-01-08T12:00:00Z",
  "expires_at": "2025-02-07T12:00:00Z",
  "last_used_at": "2025-01-10T15:30:00Z",
  "is_active": true
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 404 | Device not found |
| 403 | Device belongs to another user |

---

### DELETE /auth/2fa/devices/{device_id}

Revoke a specific trusted device.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "Device trust revoked successfully"
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 404 | Device not found |
| 403 | Device belongs to another user |

---

### DELETE /auth/2fa/devices

Revoke ALL trusted devices for the user.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "Revoked trust for 3 device(s)"
}
```

## Device Token Handling

### Web Browsers (Recommended)

Use HTTP-only cookies for security:

**Server sets cookie on trust:**
```
Set-Cookie: device_token=abc123...; HttpOnly; Secure; SameSite=Strict; Path=/; Expires=...
```

**Browser automatically sends cookie on login:**
```
Cookie: device_token=abc123...
```

### Mobile Apps / API Clients

Use custom header:

```
X-Device-Token: abc123...
```

### Token Storage Recommendations

| Platform | Recommended Storage | Security Level |
|----------|---------------------|----------------|
| Web | HTTP-only cookie | High (XSS protected) |
| iOS | Keychain | High |
| Android | EncryptedSharedPreferences | High |
| Desktop | OS Keychain | High |

**Never store device tokens in:**
- localStorage (XSS vulnerable)
- sessionStorage (XSS vulnerable)
- Plain text files
- Unencrypted databases

## Security Considerations

### What Device Trust Does NOT Bypass

- **Password authentication** - Always required
- **Account lockout** - Still enforced
- **IP-based rate limiting** - Still enforced
- **Session validation** - JWT still validated

### What Device Trust Bypasses

- **TOTP code entry** - Only when device token is valid

### Automatic Revocation

Device trust is automatically revoked when:

1. Device token expires (max 30 days)
2. User changes password
3. User disables 2FA
4. User deletes account
5. Admin force-logs out user
6. User manually revokes device

### Security Audit Trail

All device operations are logged:

- `device_trusted` - New device trusted
- `device_trust_verified` - Device token validated
- `device_trust_failed` - Invalid device token attempt
- `device_revoked` - Single device revoked
- `all_devices_revoked` - All devices revoked

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| POST /auth/2fa/verify | 10/minute |
| Device management endpoints | Standard API limits |

## Data Retention

| Data | Retention |
|------|-----------|
| Active device tokens | Until expiry (max 30 days) |
| Expired devices | Marked inactive, cleaned daily |
| Revoked devices | 7 days then permanently deleted |
| Consent logs | Retained for audit (Law 25) |
| Security audit logs | Retained per policy |

## Example: Complete Trust Flow

### Step 1: Login (triggers 2FA)

```bash
curl -X POST https://api.example.com/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=MyPassword123"
```

Response:
```json
{
  "requires_2fa": true,
  "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "2FA verification required"
}
```

### Step 2: Verify with Device Trust

```bash
curl -X POST https://api.example.com/auth/2fa/verify \
  -H "Content-Type: application/json" \
  -d '{
    "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "code": "123456",
    "trust_device": true,
    "trust_duration_days": 30,
    "consent_given": true
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "device_token": "dGhpcyBpcyBhIHNlY3VyZSBkZXZpY2UgdG9rZW4...",
  "device_expires_at": "2025-02-07T12:00:00Z"
}
```

### Step 3: Future Login (Device Trusted)

```bash
curl -X POST https://api.example.com/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Device-Token: dGhpcyBpcyBhIHNlY3VyZSBkZXZpY2UgdG9rZW4..." \
  -d "username=user@example.com&password=MyPassword123"
```

Response (no 2FA required):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Frontend Integration Notes

### Consent UI Requirements

When `trust_device` is enabled, the UI MUST:

1. Display clear explanation of what device trust means
2. Show data that will be stored (device name, expiry)
3. Provide explicit checkbox for consent
4. Link to privacy policy device trust section
5. Only enable submit when consent checkbox is checked

### Email Notification

When a device is trusted, the user receives an email containing:

- Device name (e.g., "Chrome on Windows 10")
- Trust date and time
- Expiry date
- Warning about unauthorized access
- Link to manage trusted devices
