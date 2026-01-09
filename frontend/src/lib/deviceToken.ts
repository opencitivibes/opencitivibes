/**
 * Device Token Storage Utilities
 *
 * SECURITY: Device tokens are now stored as httpOnly cookies by the backend.
 * This module only manages device ID and expiry metadata for UI purposes.
 *
 * The actual device token is:
 * - Set by backend as httpOnly cookie (inaccessible to JavaScript - XSS protection)
 * - Automatically sent by browser with requests (no manual handling needed)
 *
 * Law 25 compliance: User can view device info but not access the security token.
 */

const DEVICE_TOKEN_EXPIRY_KEY = 'device_trust_expires_at';
const DEVICE_ID_KEY = 'device_trust_device_id';

// DEPRECATED: Kept for migration cleanup only
const LEGACY_DEVICE_TOKEN_KEY = 'device_trust_token';

interface StoredDeviceInfo {
  expiresAt: string;
  deviceId?: number;
}

/**
 * Check if we have an active device trust (based on expiry).
 *
 * NOTE: This checks localStorage metadata only. The actual token validity
 * is determined by the httpOnly cookie which is not accessible to JavaScript.
 * The backend will reject invalid tokens regardless of this check.
 */
export function hasDeviceTrust(): boolean {
  if (typeof window === 'undefined') return false;

  try {
    const expiresAt = localStorage.getItem(DEVICE_TOKEN_EXPIRY_KEY);

    if (!expiresAt) return false;

    // Check if token is expired
    const expiryDate = new Date(expiresAt);
    if (isNaN(expiryDate.getTime()) || expiryDate <= new Date()) {
      // Token expired - clean up metadata
      clearDeviceInfo();
      return false;
    }

    return true;
  } catch {
    return false;
  }
}

/**
 * Store device info (NOT the token - that's in httpOnly cookie).
 * Called after successful 2FA verification with trust_device=true.
 *
 * @param expiresAt - When the device trust expires
 * @param deviceId - Optional device ID for "current device" badge
 */
export function setDeviceInfo(expiresAt: Date | string, deviceId?: number): void {
  if (typeof window === 'undefined') return;

  try {
    const expiryString = typeof expiresAt === 'string' ? expiresAt : expiresAt.toISOString();

    localStorage.setItem(DEVICE_TOKEN_EXPIRY_KEY, expiryString);
    if (deviceId !== undefined) {
      localStorage.setItem(DEVICE_ID_KEY, deviceId.toString());
    }

    // Clean up any legacy token that might exist (migration)
    localStorage.removeItem(LEGACY_DEVICE_TOKEN_KEY);
  } catch {
    // Storage failed - log warning but don't throw
    console.warn('Failed to store device info');
  }
}

/**
 * Clear stored device info.
 * Called on logout, token expiry, or explicit revocation.
 *
 * NOTE: This clears localStorage metadata only. The httpOnly cookie
 * is cleared by the backend on revocation or logout.
 */
export function clearDeviceInfo(): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.removeItem(DEVICE_TOKEN_EXPIRY_KEY);
    localStorage.removeItem(DEVICE_ID_KEY);
    // Also clean up any legacy token
    localStorage.removeItem(LEGACY_DEVICE_TOKEN_KEY);
  } catch {
    // Ignore errors during cleanup
  }
}

/**
 * Get the expiration date of the device trust.
 * Returns null if no device trust exists.
 */
export function getDeviceTrustExpiry(): Date | null {
  if (typeof window === 'undefined') return null;

  try {
    const expiresAt = localStorage.getItem(DEVICE_TOKEN_EXPIRY_KEY);
    if (!expiresAt) return null;

    const expiryDate = new Date(expiresAt);
    if (isNaN(expiryDate.getTime())) return null;

    return expiryDate;
  } catch {
    return null;
  }
}

/**
 * Get the number of days until the device trust expires.
 * Returns null if no device trust exists.
 */
export function getDaysUntilExpiry(): number | null {
  const expiry = getDeviceTrustExpiry();
  if (!expiry) return null;

  const now = new Date();
  const diffMs = expiry.getTime() - now.getTime();
  if (diffMs <= 0) return 0;

  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

/**
 * Get stored device info for display purposes.
 * Returns null if no device trust exists.
 */
export function getStoredDeviceInfo(): StoredDeviceInfo | null {
  if (typeof window === 'undefined') return null;

  try {
    const expiresAt = localStorage.getItem(DEVICE_TOKEN_EXPIRY_KEY);
    const deviceIdStr = localStorage.getItem(DEVICE_ID_KEY);

    if (!expiresAt) return null;

    const deviceId = deviceIdStr ? parseInt(deviceIdStr, 10) : undefined;

    return { expiresAt, deviceId: isNaN(deviceId as number) ? undefined : deviceId };
  } catch {
    return null;
  }
}

/**
 * Get the stored device ID for the current trusted device.
 * Returns null if no device trust exists.
 * Used for "current device" badge in device management UI.
 */
export function getStoredDeviceId(): number | null {
  if (typeof window === 'undefined') return null;

  // First check if we have device trust
  if (!hasDeviceTrust()) return null;

  try {
    const deviceIdStr = localStorage.getItem(DEVICE_ID_KEY);
    if (!deviceIdStr) return null;

    const deviceId = parseInt(deviceIdStr, 10);
    return isNaN(deviceId) ? null : deviceId;
  } catch {
    return null;
  }
}

// ============================================================================
// DEPRECATED FUNCTIONS - For backwards compatibility only
// ============================================================================

/**
 * @deprecated Device tokens are now stored as httpOnly cookies.
 * This function is kept for backwards compatibility during migration.
 * It now returns null always since tokens are not accessible to JavaScript.
 */
export function getDeviceToken(): string | null {
  // SECURITY: Device tokens are now in httpOnly cookies (not accessible)
  // Return null to indicate token is not available in JavaScript
  // The browser will automatically send the cookie with requests
  return null;
}

/**
 * @deprecated Use setDeviceInfo() instead.
 * This function is kept for backwards compatibility during migration.
 */
export function setDeviceToken(token: string, expiresAt: Date | string, deviceId?: number): void {
  // SECURITY: Don't store token in localStorage anymore
  // Just store the metadata
  setDeviceInfo(expiresAt, deviceId);
}

/**
 * @deprecated Use clearDeviceInfo() instead.
 * This function is kept for backwards compatibility during migration.
 */
export function clearDeviceToken(): void {
  clearDeviceInfo();
}

/**
 * @deprecated Use hasDeviceTrust() instead.
 */
export function isDeviceTokenValid(): boolean {
  return hasDeviceTrust();
}

/**
 * @deprecated Use getDeviceTrustExpiry() instead.
 */
export function getTokenExpiry(): Date | null {
  return getDeviceTrustExpiry();
}

/**
 * @deprecated Use getStoredDeviceInfo() instead.
 */
export function getStoredDeviceTokenInfo(): StoredDeviceInfo | null {
  return getStoredDeviceInfo();
}
