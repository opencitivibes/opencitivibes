'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { Input } from '@/components/Input';
import { Button } from '@/components/Button';
import { Mail, ArrowLeft } from 'lucide-react';

interface EmailLoginFormProps {
  onCodeSent: () => void;
  onBack: () => void;
}

export function EmailLoginForm({ onCodeSent, onBack }: EmailLoginFormProps) {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const { isLoading, requestEmailLogin } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError(t('auth.emailRequired'));
      return;
    }

    try {
      await requestEmailLogin(email.trim());
      onCodeSent();
    } catch {
      setError(t('auth.emailLoginError'));
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="text-center mb-6">
        <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
          <Mail className="w-6 h-6 text-primary-600 dark:text-primary-400" />
        </div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          {t('auth.loginByEmail')}
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
          {t('auth.loginByEmailDescription')}
        </p>
      </div>

      <Input
        id="email"
        type="email"
        label={t('auth.email')}
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder={t('auth.emailPlaceholder')}
        disabled={isLoading}
        autoComplete="email"
        autoFocus
      />

      {error && (
        <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-3 rounded-md">
          {error}
        </div>
      )}

      <Button
        type="submit"
        variant="primary"
        loading={isLoading}
        disabled={isLoading}
        className="w-full"
      >
        {isLoading ? t('auth.sendingCode') : t('auth.sendCode')}
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
