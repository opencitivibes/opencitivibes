'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { Input } from '@/components/Input';
import { Button } from '@/components/Button';
import { Alert } from '@/components/Alert';
import { PageContainer } from '@/components/PageContainer';
import { Card } from '@/components/Card';
import { LoginMethodSelector, type LoginMethod } from '@/components/LoginMethodSelector';
import { EmailLoginForm } from '@/components/EmailLoginForm';
import { EmailCodeVerification } from '@/components/EmailCodeVerification';
import { getSafeRedirect } from '@/lib/utils';

type EmailLoginStep = 'form' | 'verify';

export default function SignInPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useAuthStore((state) => state.login);
  const emailLogin = useAuthStore((state) => state.emailLogin);
  const clearEmailLoginState = useAuthStore((state) => state.clearEmailLoginState);
  const redirectUrl = getSafeRedirect(searchParams.get('redirect'));

  // Password login state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Login method state
  const [loginMethod, setLoginMethod] = useState<LoginMethod>('password');
  const [emailLoginStep, setEmailLoginStep] = useState<EmailLoginStep>('form');

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      router.push(redirectUrl);
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      if (axiosError.response?.status === 429) {
        setError(t('auth.rateLimitExceeded'));
      } else if (axiosError.response?.status === 401) {
        setError(t('auth.invalidCredentials'));
      } else {
        setError(axiosError.response?.data?.detail || t('common.error'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmailCodeSent = () => {
    setEmailLoginStep('verify');
  };

  const handleBackToEmailForm = () => {
    setEmailLoginStep('form');
    clearEmailLoginState();
  };

  const handleBackToPassword = () => {
    setLoginMethod('password');
    setEmailLoginStep('form');
    clearEmailLoginState();
  };

  const handleEmailLoginSuccess = () => {
    router.push(redirectUrl);
  };

  // Render email login flow
  if (loginMethod === 'email') {
    return (
      <PageContainer maxWidth="md" paddingY="xl">
        <Card className="max-w-md mx-auto">
          {emailLoginStep === 'form' ? (
            <EmailLoginForm onCodeSent={handleEmailCodeSent} onBack={handleBackToPassword} />
          ) : (
            <EmailCodeVerification
              email={emailLogin.emailLoginEmail!}
              expiresAt={emailLogin.emailLoginExpiresAt!}
              onBack={handleBackToEmailForm}
              onSuccess={handleEmailLoginSuccess}
            />
          )}
        </Card>
      </PageContainer>
    );
  }

  // Render password login form
  return (
    <PageContainer maxWidth="md" paddingY="xl">
      <Card className="max-w-md mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-6 text-center">
          {t('auth.signIn')}
        </h1>

        {/* Method Selector */}
        <div className="mb-6">
          <LoginMethodSelector currentMethod={loginMethod} onMethodChange={setLoginMethod} />
        </div>

        {error && (
          <div className="mb-6">
            <Alert variant="error" dismissible onDismiss={() => setError('')}>
              {error}
            </Alert>
          </div>
        )}

        <form onSubmit={handlePasswordSubmit} className="space-y-5">
          <Input
            type="email"
            label={t('auth.email')}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="exemple@email.com"
            autoComplete="email"
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('auth.password')}
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="w-full px-4 py-2.5 pr-10 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 placeholder-gray-400 dark:placeholder-gray-500 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                aria-label={showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
              >
                {showPassword ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.542 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                    />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                    />
                  </svg>
                )}
              </button>
            </div>
          </div>

          <Button
            type="submit"
            variant="primary"
            loading={isLoading}
            disabled={isLoading}
            className="w-full"
          >
            {isLoading ? t('common.loading') : t('auth.signInButton')}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
          {t('auth.dontHaveAccount')}{' '}
          <Link
            href="/signup"
            className="text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium transition-colors"
          >
            {t('auth.signUpHere')}
          </Link>
        </p>
      </Card>
    </PageContainer>
  );
}
