'use client';

import { useState, useRef, useEffect, type ReactNode, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useBetaAccess } from '@/hooks/useBetaAccess';
import { Button } from './Button';
import { Eye, EyeOff, Lock } from 'lucide-react';

interface BetaAccessGateProps {
  children: ReactNode;
}

/**
 * Beta access gate component that blocks access to the site until
 * the correct password is entered. Only active when NEXT_PUBLIC_BETA_MODE=true.
 */
export function BetaAccessGate({ children }: BetaAccessGateProps) {
  const { t } = useTranslation();
  const { isUnlocked, error, unlock } = useBetaAccess();
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  const isBetaMode = process.env.NEXT_PUBLIC_BETA_MODE === 'true';

  // Focus input when modal appears
  useEffect(() => {
    if (isBetaMode && !isUnlocked) {
      inputRef.current?.focus();
    }
  }, [isBetaMode, isUnlocked]);

  // Trap focus within modal
  useEffect(() => {
    if (!isBetaMode || isUnlocked) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab' && modalRef.current) {
        const focusableElements = modalRef.current.querySelectorAll(
          'input, button, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0] as HTMLElement;
        const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isBetaMode, isUnlocked]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Small delay for UX
    setTimeout(() => {
      unlock(password);
      setIsSubmitting(false);
    }, 300);
  };

  // If beta mode is disabled, render children normally
  if (!isBetaMode) {
    return <>{children}</>;
  }

  // If unlocked, render children normally
  if (isUnlocked) {
    return <>{children}</>;
  }

  // Show beta gate
  return (
    <>
      {/* Blurred content behind */}
      <div className="blur-md pointer-events-none select-none" aria-hidden="true">
        {children}
      </div>

      {/* Overlay */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50" aria-hidden="true" />

      {/* Modal */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="beta-title"
        aria-describedby="beta-description"
      >
        <div
          ref={modalRef}
          className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full p-8 animate-in fade-in zoom-in-95 duration-200"
        >
          {/* Icon */}
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center">
              <Lock className="w-8 h-8 text-primary-600 dark:text-primary-400" />
            </div>
          </div>

          {/* Title */}
          <h1
            id="beta-title"
            className="text-2xl font-bold text-center text-gray-900 dark:text-white mb-2"
          >
            {t('beta.title')}
          </h1>

          {/* Description */}
          <p id="beta-description" className="text-center text-gray-600 dark:text-gray-400 mb-6">
            {t('beta.description')}
          </p>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Password input with show/hide toggle */}
            <div className="relative">
              <label htmlFor="beta-password" className="sr-only">
                {t('beta.passwordPlaceholder')}
              </label>
              <input
                ref={inputRef}
                id="beta-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('beta.passwordPlaceholder')}
                className={`w-full px-4 py-3 pr-12 rounded-lg text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 ${
                  error ? 'border-2 border-red-500' : 'border border-gray-300 dark:border-gray-600'
                }`}
                autoComplete="off"
                aria-invalid={error ? 'true' : 'false'}
                aria-describedby={error ? 'beta-error' : undefined}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none focus:text-primary-500"
                aria-label={showPassword ? t('beta.hidePassword') : t('beta.showPassword')}
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>

            {/* Error message */}
            {error && (
              <p
                id="beta-error"
                className="text-sm text-red-600 dark:text-red-400 text-center"
                role="alert"
              >
                {t('beta.error')}
              </p>
            )}

            {/* Submit button */}
            <Button
              type="submit"
              className="w-full"
              size="lg"
              loading={isSubmitting}
              disabled={!password.trim()}
            >
              {t('beta.submit')}
            </Button>
          </form>
        </div>
      </div>
    </>
  );
}
