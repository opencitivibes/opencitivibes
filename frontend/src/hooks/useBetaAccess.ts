'use client';

import { useState, useCallback, useSyncExternalStore } from 'react';

const STORAGE_KEY = 'beta_unlocked';

interface UseBetaAccessReturn {
  isUnlocked: boolean;
  isLoading: boolean;
  error: string | null;
  unlock: (password: string) => boolean;
}

/**
 * Helper to read localStorage value safely (client-side only).
 */
function getStoredValue(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(STORAGE_KEY) === 'true';
}

/**
 * Subscribe to storage events for external sync.
 */
function subscribe(callback: () => void): () => void {
  window.addEventListener('storage', callback);
  return () => window.removeEventListener('storage', callback);
}

/**
 * Hook to manage beta access gate state.
 * Uses useSyncExternalStore for proper SSR hydration.
 */
export function useBetaAccess(): UseBetaAccessReturn {
  const isUnlocked = useSyncExternalStore(
    subscribe,
    getStoredValue,
    () => false // Server snapshot - always locked
  );

  const [error, setError] = useState<string | null>(null);

  const unlock = useCallback((password: string): boolean => {
    setError(null);
    const correctPassword = process.env.NEXT_PUBLIC_BETA_PASSWORD;

    if (!correctPassword) {
      // No password configured - allow access
      localStorage.setItem(STORAGE_KEY, 'true');
      window.dispatchEvent(new Event('storage'));
      return true;
    }

    if (password === correctPassword) {
      localStorage.setItem(STORAGE_KEY, 'true');
      window.dispatchEvent(new Event('storage'));
      return true;
    }

    setError('incorrect');
    return false;
  }, []);

  // No loading state needed with useSyncExternalStore
  return { isUnlocked, isLoading: false, error, unlock };
}
