'use client';

import { useState, useCallback, useEffect } from 'react';
import { betaAPI } from '@/lib/api';

interface UseBetaAccessReturn {
  isUnlocked: boolean;
  isLoading: boolean;
  error: string | null;
  isBetaMode: boolean;
  unlock: (password: string) => Promise<boolean>;
}

/**
 * Hook to manage beta access gate state with server-side verification.
 *
 * Security: Password verification happens server-side to prevent
 * client-side exposure of the beta password (V1 security fix).
 */
export function useBetaAccess(): UseBetaAccessReturn {
  const [isUnlocked, setIsUnlocked] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isBetaMode, setIsBetaMode] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Check beta status on mount
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await betaAPI.getStatus();
        setIsBetaMode(status.beta_mode_enabled);
        setIsUnlocked(status.has_access);
      } catch {
        // If API fails, assume beta mode is disabled
        setIsBetaMode(false);
        setIsUnlocked(true);
      } finally {
        setIsLoading(false);
      }
    };

    checkStatus();
  }, []);

  const unlock = useCallback(async (password: string): Promise<boolean> => {
    setError(null);

    try {
      const response = await betaAPI.verify(password);
      if (response.success) {
        setIsUnlocked(true);
        return true;
      }
      // This shouldn't happen - API throws on failure
      setError('incorrect');
      return false;
    } catch (err: unknown) {
      // Check for rate limiting (429)
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { status?: number } };
        if (axiosError.response?.status === 429) {
          setError('rate_limited');
          return false;
        }
      }
      // Generic error for incorrect password
      setError('incorrect');
      return false;
    }
  }, []);

  return {
    isUnlocked: !isBetaMode || isUnlocked,
    isLoading,
    error,
    isBetaMode,
    unlock,
  };
}
