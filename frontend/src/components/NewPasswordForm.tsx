'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { Input } from '@/components/Input';
import { Button } from '@/components/Button';
import {
  PasswordStrengthIndicator,
  validatePassword,
} from '@/components/PasswordStrengthIndicator';
import { Lock, ArrowLeft, CheckCircle, Eye, EyeOff } from 'lucide-react';

interface NewPasswordFormProps {
  email: string;
  tokenExpiresAt: Date;
  onSuccess: () => void;
  onBack: () => void;
}

export function NewPasswordForm({
  email,
  tokenExpiresAt,
  onSuccess,
  onBack,
}: NewPasswordFormProps) {
  const { t } = useTranslation();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState(0);
  const { isLoading, resetPassword, clearSensitiveResetData } = useAuthStore();

  // Timer countdown for token expiry (Finding #5)
  useEffect(() => {
    const updateTimer = () => {
      const remaining = Math.max(0, Math.floor((tokenExpiresAt.getTime() - Date.now()) / 1000));
      setTimeLeft(remaining);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [tokenExpiresAt]);

  // Clear sensitive data on unmount (Finding #5)
  useEffect(() => {
    return () => {
      clearSensitiveResetData();
    };
  }, [clearSensitiveResetData]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError(null);

      // Validate passwords match
      if (password !== confirmPassword) {
        setError(t('auth.passwordsDoNotMatch'));
        return;
      }

      // Validate password strength (synced with backend - Finding #10)
      const validation = validatePassword(password);
      if (!validation.isValid) {
        setError(t('auth.passwordRequirements'));
        return;
      }

      // Check if token expired
      if (timeLeft <= 0) {
        setError(t('auth.resetTokenExpired'));
        return;
      }

      try {
        await resetPassword(password);
        onSuccess();
      } catch {
        setError(t('auth.resetPasswordError'));
      }
    },
    [password, confirmPassword, resetPassword, onSuccess, timeLeft, t]
  );

  const validation = validatePassword(password);
  const passwordsMatch = password === confirmPassword && password.length > 0;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="text-center mb-6">
        <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <Lock className="w-6 h-6 text-primary-600 dark:text-primary-400" />
        </div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          {t('auth.setNewPassword')}
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">{email}</p>
      </div>

      {/* Token expiry countdown (Finding #5) */}
      <div className="text-center text-sm">
        {timeLeft > 0 ? (
          <span className="text-gray-600 dark:text-gray-400">
            {t('auth.tokenExpiresIn', { time: formatTime(timeLeft) })}
          </span>
        ) : (
          <span className="text-red-600 dark:text-red-400">{t('auth.resetTokenExpired')}</span>
        )}
      </div>

      {/* New Password Input */}
      <div className="relative">
        <Input
          id="new-password"
          type={showPassword ? 'text' : 'password'}
          label={t('auth.newPassword')}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={t('auth.newPasswordPlaceholder')}
          disabled={isLoading || timeLeft <= 0}
          autoComplete="new-password"
          autoFocus
        />
        <button
          type="button"
          className="absolute right-3 top-9 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          onClick={() => setShowPassword(!showPassword)}
          tabIndex={-1}
          aria-label={showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
        >
          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>

      {/* Password Strength Indicator */}
      <PasswordStrengthIndicator password={password} showRequirements={true} />

      {/* Confirm Password Input */}
      <div className="relative">
        <Input
          id="confirm-password"
          type={showConfirmPassword ? 'text' : 'password'}
          label={t('auth.confirmPassword')}
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder={t('auth.confirmPasswordPlaceholder')}
          disabled={isLoading || timeLeft <= 0}
          autoComplete="new-password"
        />
        <button
          type="button"
          className="absolute right-3 top-9 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
          tabIndex={-1}
          aria-label={showConfirmPassword ? t('auth.hidePassword') : t('auth.showPassword')}
        >
          {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>

      {/* Passwords match indicator */}
      {confirmPassword.length > 0 && (
        <div
          className={`flex items-center gap-2 text-xs ${
            passwordsMatch ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
          }`}
        >
          {passwordsMatch ? (
            <>
              <CheckCircle className="w-3 h-3" />
              <span>{t('auth.passwordsMatch')}</span>
            </>
          ) : (
            <span>{t('auth.passwordsDoNotMatch')}</span>
          )}
        </div>
      )}

      {error && (
        <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-3 rounded-md">
          {error}
        </div>
      )}

      <Button
        type="submit"
        variant="primary"
        loading={isLoading}
        disabled={isLoading || !validation.isValid || !passwordsMatch || timeLeft <= 0}
        className="w-full"
      >
        {isLoading ? t('auth.resetting') : t('auth.resetPassword')}
      </Button>

      <Button
        type="button"
        variant="ghost"
        className="w-full"
        onClick={onBack}
        disabled={isLoading}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        {t('auth.backToLogin')}
      </Button>
    </form>
  );
}
