import { create } from 'zustand';
import { setUser } from '@/lib/sentry-utils';
import { authAPI, setAuthFailureHandler } from '@/lib/api';
import type { User } from '@/types';

// Refresh token 5 minutes before expiry
const TOKEN_REFRESH_MARGIN_MS = 5 * 60 * 1000;

// Store the refresh timer globally so it can be cleared
let refreshTimer: ReturnType<typeof setTimeout> | null = null;

// Email login state interface
interface EmailLoginState {
  emailLoginEmail: string | null;
  emailLoginPending: boolean;
  emailLoginExpiresAt: Date | null;
}

const initialEmailLoginState: EmailLoginState = {
  emailLoginEmail: null,
  emailLoginPending: false,
  emailLoginExpiresAt: null,
};

/**
 * Decode JWT payload without verification (for reading expiry).
 * Validates payload structure to prevent prototype pollution and crashes.
 */
function decodeJwtPayload(token: string): { exp?: number; sub?: string } | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payloadPart = parts[1];
    if (!payloadPart) return null;
    const payload = JSON.parse(atob(payloadPart));

    // Validate structure
    if (typeof payload !== 'object' || payload === null) return null;

    // Validate and extract only expected fields (prevents prototype pollution)
    const result: { exp?: number; sub?: string } = {};

    if (payload.exp !== undefined) {
      if (typeof payload.exp !== 'number') return null;
      result.exp = payload.exp;
    }

    if (payload.sub !== undefined) {
      if (typeof payload.sub !== 'string') return null;
      result.sub = payload.sub;
    }

    return result;
  } catch {
    return null;
  }
}

/**
 * Schedule token refresh before expiry
 */
function scheduleTokenRefresh(token: string, refreshCallback: () => Promise<void>): void {
  // Clear any existing timer
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }

  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return;

  const expiryMs = payload.exp * 1000;
  const now = Date.now();
  const timeUntilRefresh = expiryMs - now - TOKEN_REFRESH_MARGIN_MS;

  // Only schedule if there's time remaining (at least 1 minute)
  if (timeUntilRefresh > 60 * 1000) {
    refreshTimer = setTimeout(() => {
      refreshCallback().catch(() => {
        // Refresh failed - user will be logged out when token expires
      });
    }, timeUntilRefresh);
  }
}

/**
 * Clear any scheduled token refresh
 */
function clearTokenRefresh(): void {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  sessionExpired: boolean;
  accountDeleted: boolean;

  // Email login state
  emailLogin: EmailLoginState;

  // Existing methods
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    username: string,
    displayName: string,
    password: string,
    acceptsTerms: boolean,
    acceptsPrivacyPolicy: boolean,
    marketingConsent: boolean,
    requestsOfficialStatus?: boolean,
    officialTitleRequest?: string
  ) => Promise<{ requestedOfficial: boolean }>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  clearSessionExpired: () => void;
  setAccountDeleted: () => void;
  clearAccountDeleted: () => void;
  refreshToken: (retryCount?: number) => Promise<void>;

  // Email login methods
  requestEmailLogin: (email: string) => Promise<number>;
  verifyEmailCode: (email: string, code: string) => Promise<void>;
  clearEmailLoginState: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  isLoading: false,
  sessionExpired: false,
  accountDeleted: false,
  emailLogin: initialEmailLoginState,

  login: async (email: string, password: string) => {
    set({ isLoading: true });
    try {
      const tokenResponse = await authAPI.login({ username: email, password });
      if (typeof window !== 'undefined') {
        localStorage.setItem('token', tokenResponse.access_token);
      }
      set({ token: tokenResponse.access_token });

      // Schedule token refresh
      scheduleTokenRefresh(tokenResponse.access_token, get().refreshToken);

      const user = await authAPI.getMe();

      // Set Sentry user context (ID only - no PII, no-op if Sentry disabled)
      setUser({
        id: user.id.toString(),
        // Do NOT include email or username for privacy
      });

      set({ user, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  register: async (
    email: string,
    username: string,
    displayName: string,
    password: string,
    acceptsTerms: boolean,
    acceptsPrivacyPolicy: boolean,
    marketingConsent: boolean,
    requestsOfficialStatus?: boolean,
    officialTitleRequest?: string
  ) => {
    set({ isLoading: true });
    try {
      await authAPI.register({
        email,
        username,
        display_name: displayName,
        password,
        accepts_terms: acceptsTerms,
        accepts_privacy_policy: acceptsPrivacyPolicy,
        marketing_consent: marketingConsent,
        requests_official_status: requestsOfficialStatus,
        official_title_request: requestsOfficialStatus ? officialTitleRequest : null,
      });
      // Auto-login after registration
      const tokenResponse = await authAPI.login({ username: email, password });
      if (typeof window !== 'undefined') {
        localStorage.setItem('token', tokenResponse.access_token);
      }
      set({ token: tokenResponse.access_token });

      // Schedule token refresh
      scheduleTokenRefresh(tokenResponse.access_token, get().refreshToken);

      const user = await authAPI.getMe();

      // Set Sentry user context (ID only - no PII, no-op if Sentry disabled)
      setUser({
        id: user.id.toString(),
      });

      set({ user, isLoading: false });
      return { requestedOfficial: requestsOfficialStatus || false };
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: () => {
    // Clear token refresh timer
    clearTokenRefresh();

    // Clear Sentry user context (no-op if Sentry disabled)
    setUser(null);

    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
    set({
      user: null,
      token: null,
      sessionExpired: false,
      emailLogin: initialEmailLoginState,
    });
  },

  fetchUser: async () => {
    if (typeof window === 'undefined') return;

    const token = localStorage.getItem('token');
    if (!token) {
      clearTokenRefresh();
      setUser(null);
      set({ user: null, token: null });
      return;
    }

    try {
      const user = await authAPI.getMe();

      // Set Sentry user context (ID only - no PII, no-op if Sentry disabled)
      setUser({
        id: user.id.toString(),
      });

      set({ user, token });

      // Schedule token refresh for existing token
      scheduleTokenRefresh(token, get().refreshToken);
    } catch {
      clearTokenRefresh();
      setUser(null);
      localStorage.removeItem('token');
      set({ user: null, token: null });
    }
  },

  clearSessionExpired: () => {
    set({ sessionExpired: false });
  },

  setAccountDeleted: () => {
    set({ accountDeleted: true });
  },

  clearAccountDeleted: () => {
    set({ accountDeleted: false });
  },

  refreshToken: async (retryCount = 0) => {
    try {
      const tokenResponse = await authAPI.refreshToken();

      if (typeof window !== 'undefined') {
        localStorage.setItem('token', tokenResponse.access_token);
      }

      set({ token: tokenResponse.access_token });

      // Schedule the next refresh (reset retry count on success)
      scheduleTokenRefresh(tokenResponse.access_token, () => get().refreshToken(0));
    } catch (error) {
      // Only retry on network errors (not 401/403 auth failures)
      // Axios errors have a 'response' property when the server responds
      const isNetworkError = error instanceof Error && !('response' in error);

      if (isNetworkError && retryCount < 3) {
        // Retry with exponential backoff: 1s, 2s, 4s
        const delay = Math.pow(2, retryCount) * 1000;
        setTimeout(() => get().refreshToken(retryCount + 1), delay);
        return;
      }

      // Final failure or auth error - clear state and let 401 handler deal with it
      clearTokenRefresh();
    }
  },

  // Email Login Methods
  requestEmailLogin: async (email: string) => {
    set({ isLoading: true });
    try {
      const response = await authAPI.requestEmailLogin(email);

      const expiresAt = new Date(Date.now() + response.expires_in_seconds * 1000);

      set({
        isLoading: false,
        emailLogin: {
          emailLoginEmail: email,
          emailLoginPending: true,
          emailLoginExpiresAt: expiresAt,
        },
      });

      return response.expires_in_seconds;
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  verifyEmailCode: async (email: string, code: string) => {
    set({ isLoading: true });
    try {
      const tokenResponse = await authAPI.verifyEmailCode(email, code);

      if (typeof window !== 'undefined') {
        localStorage.setItem('token', tokenResponse.access_token);
      }
      set({ token: tokenResponse.access_token });

      // Schedule token refresh
      scheduleTokenRefresh(tokenResponse.access_token, get().refreshToken);

      const user = await authAPI.getMe();

      setUser({
        id: user.id.toString(),
      });

      set({
        user,
        isLoading: false,
        emailLogin: initialEmailLoginState,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  clearEmailLoginState: () => {
    set({ emailLogin: initialEmailLoginState });
  },
}));

// Register auth failure handler after store is created
if (typeof window !== 'undefined') {
  setAuthFailureHandler(() => {
    // Clear token refresh timer
    clearTokenRefresh();

    // Clear Sentry user context (no-op if Sentry disabled)
    setUser(null);

    // Set session expired flag and logout
    useAuthStore.setState({
      sessionExpired: true,
      user: null,
      token: null,
      emailLogin: initialEmailLoginState,
    });

    // Redirect to homepage
    if (window.location.pathname !== '/') {
      window.location.href = '/';
    }
  });
}
