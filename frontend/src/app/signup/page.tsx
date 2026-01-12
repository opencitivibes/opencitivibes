'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Trans, useTranslation } from 'react-i18next';
import { Shield, Info, FileText, AlertCircle, Calendar, Mail } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { Input } from '@/components/Input';
import { Button } from '@/components/Button';
import { Alert } from '@/components/Alert';
import { PageContainer } from '@/components/PageContainer';
import { Card } from '@/components/Card';
import { PasswordStrengthIndicator } from '@/components/PasswordStrengthIndicator';
import {
  calculateAge,
  isMinorRequiringConsent,
  formatDateForInput,
  getMinDateOfBirth,
  getMaxDateOfBirth,
  parseDateString,
} from '@/utils/age';

/** Success state for minors awaiting parental consent */
interface PendingConsentState {
  userId: number;
  parentEmail: string;
}

export default function SignUpPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const register = useAuthStore((state) => state.register);
  const errorRef = useRef<HTMLDivElement>(null);

  // Basic form fields
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Law 25 minors protection fields
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [parentEmail, setParentEmail] = useState('');
  const [isMinor, setIsMinor] = useState(false);

  // Official request fields
  const [requestsOfficial, setRequestsOfficial] = useState(false);
  const [officialTitleRequest, setOfficialTitleRequest] = useState('');

  // Form state
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Success state for minors
  const [pendingConsent, setPendingConsent] = useState<PendingConsentState | null>(null);

  // Law 25 consent fields
  const [acceptsTerms, setAcceptsTerms] = useState(false);
  const [acceptsPrivacy, setAcceptsPrivacy] = useState(false);
  const [marketingConsent, setMarketingConsent] = useState(false);

  // Date constraints for the date picker
  const minDate = formatDateForInput(getMinDateOfBirth());
  const maxDate = formatDateForInput(getMaxDateOfBirth());

  // Calculate age when date of birth changes
  useEffect(() => {
    if (dateOfBirth) {
      const dob = parseDateString(dateOfBirth);
      if (dob) {
        setIsMinor(isMinorRequiringConsent(dob));
      } else {
        setIsMinor(false);
      }
    } else {
      setIsMinor(false);
    }
  }, [dateOfBirth]);

  // Scroll to error when it appears
  useEffect(() => {
    if (error && errorRef.current) {
      errorRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [error]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate date of birth
    if (!dateOfBirth) {
      setError(t('validation.dateOfBirthRequired'));
      return;
    }

    const dob = parseDateString(dateOfBirth);
    if (!dob) {
      setError(t('validation.invalidDateOfBirth'));
      return;
    }

    // Show age for validation
    const age = calculateAge(dob);
    if (age < 0 || age > 150) {
      setError(t('validation.invalidDateOfBirth'));
      return;
    }

    // Validate parent email for minors
    if (isMinor) {
      if (!parentEmail) {
        setError(t('validation.parentEmailRequired'));
        return;
      }
      if (parentEmail.toLowerCase() === email.toLowerCase()) {
        setError(t('validation.parentEmailDifferent'));
        return;
      }
    }

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
        dateOfBirth,
        isMinor ? parentEmail : undefined,
        requestsOfficial,
        officialTitleRequest
      );

      // Handle parental consent required
      if (result.requiresParentalConsent) {
        setPendingConsent({
          userId: result.pendingConsentId || 0,
          parentEmail: result.parentEmail || parentEmail,
        });
        return;
      }

      // Standard registration flow
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

  // If parental consent is pending, show success message
  if (pendingConsent) {
    return (
      <PageContainer maxWidth="md" paddingY="xl">
        <Card className="max-w-md mx-auto">
          <div className="text-center">
            <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-4">
              <Mail className="w-8 h-8 text-green-600 dark:text-green-400" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              {t('signup.pendingConsent.title')}
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {t('signup.pendingConsent.message', { parentEmail: pendingConsent.parentEmail })}
            </p>

            <Alert variant="info" className="mb-6 text-left">
              <div className="flex items-start gap-2">
                <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <p className="text-sm">{t('signup.pendingConsent.checkInbox')}</p>
              </div>
            </Alert>

            <div className="space-y-3">
              <Link
                href="/"
                className="block w-full px-4 py-2.5 text-center bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
              >
                {t('signup.goToHome')}
              </Link>
            </div>
          </div>
        </Card>
      </PageContainer>
    );
  }

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

          {/* Date of Birth - Law 25 requirement */}
          <div>
            <label
              htmlFor="dateOfBirth"
              className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
            >
              <Calendar className="w-4 h-4" />
              {t('auth.dateOfBirth')}
              <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              id="dateOfBirth"
              value={dateOfBirth}
              onChange={(e) => setDateOfBirth(e.target.value)}
              required
              min={minDate}
              max={maxDate}
              aria-describedby="dateOfBirthHelp"
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <p id="dateOfBirthHelp" className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">
              {t('auth.dateOfBirthHelp')}
            </p>
          </div>

          {/* Parental Consent Alert - shown when user is under 14 */}
          {isMinor && (
            <div
              className="p-4 border border-amber-200 dark:border-amber-700 rounded-xl bg-amber-50 dark:bg-amber-900/20"
              role="alert"
              aria-live="polite"
            >
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-200">
                    {t('signup.parentalConsentRequired')}
                  </h3>
                  <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
                    {t('signup.parentalConsentExplanation')}
                  </p>
                </div>
              </div>

              {/* Parent Email Field */}
              <div className="mt-4">
                <label
                  htmlFor="parentEmail"
                  className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  <Mail className="w-4 h-4" />
                  {t('auth.parentEmail')}
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  id="parentEmail"
                  value={parentEmail}
                  onChange={(e) => setParentEmail(e.target.value)}
                  required={isMinor}
                  aria-describedby="parentEmailHelp"
                  placeholder="parent@email.com"
                  className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <p id="parentEmailHelp" className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">
                  {t('auth.parentEmailHelp')}
                </p>
              </div>
            </div>
          )}

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
