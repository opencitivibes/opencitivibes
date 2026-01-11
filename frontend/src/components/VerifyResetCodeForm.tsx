'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/Button';
import { ArrowLeft, RefreshCw, ShieldCheck } from 'lucide-react';

interface VerifyResetCodeFormProps {
  email: string;
  expiresAt: Date;
  onVerified: () => void;
  onBack: () => void;
  onResend: () => Promise<void>;
}

export function VerifyResetCodeForm({
  email,
  expiresAt,
  onVerified,
  onBack,
  onResend,
}: VerifyResetCodeFormProps) {
  const { t } = useTranslation();
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState(0);
  const [canResend, setCanResend] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const { isLoading, verifyPasswordResetCode } = useAuthStore();

  // Timer countdown
  useEffect(() => {
    const updateTimer = () => {
      const remaining = Math.max(0, Math.floor((expiresAt.getTime() - Date.now()) / 1000));
      setTimeLeft(remaining);

      if (remaining <= 0) {
        setCanResend(true);
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [expiresAt]);

  // Focus first input on mount
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  const handleVerify = useCallback(
    async (codeString?: string) => {
      const fullCode = codeString || code.join('');

      if (fullCode.length !== 6) {
        setError(t('auth.codeIncomplete'));
        return;
      }

      try {
        await verifyPasswordResetCode(email, fullCode);
        onVerified();
      } catch {
        setError(t('auth.codeVerificationError'));
        // Clear code on error
        setCode(['', '', '', '', '', '']);
        inputRefs.current[0]?.focus();
      }
    },
    [code, email, verifyPasswordResetCode, onVerified, t]
  );

  const handleInputChange = (index: number, value: string) => {
    // Only allow digits
    const digit = value.replace(/\D/g, '').slice(-1);

    const newCode = [...code];
    newCode[index] = digit;
    setCode(newCode);
    setError(null);

    // Auto-advance to next input
    if (digit && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all digits entered
    if (digit && index === 5) {
      const fullCode = newCode.join('');
      if (fullCode.length === 6) {
        handleVerify(fullCode);
      }
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      // Move to previous input on backspace if current is empty
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);

    if (pasted.length === 6) {
      const newCode = pasted.split('');
      setCode(newCode);
      setError(null);
      inputRefs.current[5]?.focus();
      handleVerify(pasted);
    }
  };

  const handleResend = async () => {
    setError(null);
    setIsResending(true);
    try {
      await onResend();
      setCanResend(false);
      setCode(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } catch {
      setError(t('auth.resendError'));
    } finally {
      setIsResending(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <ShieldCheck className="w-6 h-6 text-primary-600 dark:text-primary-400" />
        </div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          {t('auth.enterResetCode')}
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
          {t('auth.resetCodeSentTo', { email })}
        </p>
      </div>

      {/* Code Input */}
      <div className="flex justify-center gap-2" onPaste={handlePaste}>
        {code.map((digit, index) => (
          <input
            key={index}
            ref={(el) => {
              inputRefs.current[index] = el;
            }}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={digit}
            onChange={(e) => handleInputChange(index, e.target.value)}
            onKeyDown={(e) => handleKeyDown(index, e)}
            className="w-12 h-14 text-center text-2xl font-mono border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
            disabled={isLoading || isResending}
            aria-label={`${t('auth.codeDigit')} ${index + 1}`}
          />
        ))}
      </div>

      {/* Timer */}
      <div className="text-center text-sm text-gray-600 dark:text-gray-400">
        {timeLeft > 0 ? (
          <span>{t('auth.codeExpiresIn', { time: formatTime(timeLeft) })}</span>
        ) : (
          <span className="text-red-600 dark:text-red-400">{t('auth.codeExpired')}</span>
        )}
      </div>

      {error && (
        <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-3 rounded-md text-center">
          {error}
        </div>
      )}

      {/* Verify Button */}
      <Button
        type="button"
        variant="primary"
        className="w-full"
        onClick={() => handleVerify()}
        disabled={isLoading || isResending || code.join('').length !== 6}
        loading={isLoading}
      >
        {isLoading ? t('auth.verifying') : t('auth.verifyCode')}
      </Button>

      {/* Resend */}
      <div className="text-center">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleResend}
          disabled={!canResend || isLoading || isResending}
          loading={isResending}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          {canResend ? t('auth.resendCode') : t('auth.resendIn', { time: formatTime(timeLeft) })}
        </Button>
      </div>

      {/* Back Button */}
      <Button
        type="button"
        variant="ghost"
        className="w-full"
        onClick={onBack}
        disabled={isLoading || isResending}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        {t('auth.backToLogin')}
      </Button>
    </div>
  );
}
