'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Trans, useTranslation } from 'react-i18next';
import { Shield, Info, FileText } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { Input } from '@/components/Input';
import { Button } from '@/components/Button';
import { Alert } from '@/components/Alert';
import { PageContainer } from '@/components/PageContainer';
import { Card } from '@/components/Card';
import { PasswordStrengthIndicator } from '@/components/PasswordStrengthIndicator';

export default function SignUpPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const register = useAuthStore((state) => state.register);
  const errorRef = useRef<HTMLDivElement>(null);

  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [requestsOfficial, setRequestsOfficial] = useState(false);
  const [officialTitleRequest, setOfficialTitleRequest] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Law 25 consent fields
  const [acceptsTerms, setAcceptsTerms] = useState(false);
  const [acceptsPrivacy, setAcceptsPrivacy] = useState(false);
  const [marketingConsent, setMarketingConsent] = useState(false);

  // Scroll to error when it appears
  useEffect(() => {
    if (error && errorRef.current) {
      errorRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [error]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate consent checkboxes
    if (!acceptsTerms) {
      setError(t('signup.acceptsTermsRequired'));
      return;
    }
    if (!acceptsPrivacy) {
      setError(t('signup.acceptsPrivacyRequired'));
      return;
    }

    setIsLoading(true);

    try {
      const result = await register(
        email,
        username,
        displayName,
        password,
        acceptsTerms,
        acceptsPrivacy,
        marketingConsent,
        requestsOfficial,
        officialTitleRequest
      );
      if (result.requestedOfficial) {
        router.push('/signup/pending-official');
      } else {
        router.push('/');
      }
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{
        detail: string | Array<{ msg: string }>;
      }>;
      const detail = axiosError.response?.data?.detail;
      // Handle FastAPI validation errors (array of objects)
      if (Array.isArray(detail)) {
        setError(detail.map((e) => e.msg).join(', '));
      } else {
        setError(detail || t('common.error'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PageContainer maxWidth="md" paddingY="xl">
      <Card className="max-w-md mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-6 text-center">
          {t('auth.signUp')}
        </h1>

        {error && (
          <div ref={errorRef} className="mb-6">
            <Alert variant="error" dismissible onDismiss={() => setError('')}>
              {error}
            </Alert>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <Input
            type="email"
            label={t('auth.email')}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="exemple@email.com"
          />

          <Input
            type="text"
            label={t('auth.username')}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            placeholder="nom_utilisateur"
          />

          <Input
            type="text"
            label={t('auth.displayName')}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            placeholder={t('auth.displayNamePlaceholder')}
            helperText={t('auth.displayNameHelp')}
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('auth.password')}
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={12}
                autoComplete="new-password"
                className="w-full px-4 py-2.5 pr-10 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-400 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 transition-colors"
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
            <PasswordStrengthIndicator password={password} />
            <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">
              {t('auth.passwordHint')}
            </p>
          </div>

          {/* Law 25 Consent Section */}
          <div className="p-4 border border-primary-200 dark:border-primary-700 rounded-xl bg-primary-50 dark:bg-primary-900/20">
            <div className="flex items-center gap-2 mb-3">
              <FileText className="w-4 h-4 text-primary-600" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('signup.consentSection')}
              </span>
            </div>

            {/* Terms of Service */}
            <div className="flex items-start gap-3 mb-3">
              <input
                type="checkbox"
                id="acceptsTerms"
                checked={acceptsTerms}
                onChange={(e) => setAcceptsTerms(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <label
                htmlFor="acceptsTerms"
                className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer"
              >
                <Trans
                  i18nKey="signup.acceptsTerms"
                  components={{
                    termsLink: (
                      <Link
                        key="terms"
                        href="/terms"
                        target="_blank"
                        className="text-primary-600 hover:text-primary-700 underline"
                      />
                    ),
                  }}
                />
                <span className="text-red-500 ml-1">*</span>
              </label>
            </div>

            {/* Privacy Policy */}
            <div className="flex items-start gap-3 mb-3">
              <input
                type="checkbox"
                id="acceptsPrivacy"
                checked={acceptsPrivacy}
                onChange={(e) => setAcceptsPrivacy(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <label
                htmlFor="acceptsPrivacy"
                className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer"
              >
                <Trans
                  i18nKey="signup.acceptsPrivacy"
                  components={{
                    privacyLink: (
                      <Link
                        key="privacy"
                        href="/privacy"
                        target="_blank"
                        className="text-primary-600 hover:text-primary-700 underline"
                      />
                    ),
                  }}
                />
                <span className="text-red-500 ml-1">*</span>
              </label>
            </div>

            {/* Marketing (optional) */}
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                id="marketingConsent"
                checked={marketingConsent}
                onChange={(e) => setMarketingConsent(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <div>
                <label
                  htmlFor="marketingConsent"
                  className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer"
                >
                  {t('signup.marketingConsent')}
                </label>
                <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                  ({t('signup.marketingOptional')})
                </span>
              </div>
            </div>
          </div>

          {/* Official Request Section */}
          <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-gray-800/50">
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                id="requestsOfficial"
                checked={requestsOfficial}
                onChange={(e) => setRequestsOfficial(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <div className="flex-1">
                <label
                  htmlFor="requestsOfficial"
                  className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer"
                >
                  <Shield className="w-4 h-4 text-primary-600" />
                  {t('signup.iAmOfficial')}
                </label>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {t('signup.officialExplanation')}
                </p>
              </div>
            </div>

            {requestsOfficial && (
              <div className="mt-4">
                <label
                  htmlFor="officialTitle"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  {t('signup.officialTitle')}
                </label>
                <input
                  type="text"
                  id="officialTitle"
                  value={officialTitleRequest}
                  onChange={(e) => setOfficialTitleRequest(e.target.value)}
                  placeholder={t('signup.officialTitlePlaceholder')}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  maxLength={100}
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                  <Info className="w-3 h-3" />
                  {t('signup.officialVerificationNote')}
                </p>
              </div>
            )}
          </div>

          <Button
            type="submit"
            variant="primary"
            loading={isLoading}
            disabled={isLoading}
            className="w-full"
          >
            {isLoading ? t('common.loading') : t('auth.signUpButton')}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          {t('auth.alreadyHaveAccount')}{' '}
          <Link
            href="/signin"
            className="text-primary-600 hover:text-primary-700 font-medium transition-colors"
          >
            {t('auth.signInHere')}
          </Link>
        </p>
      </Card>
    </PageContainer>
  );
}
