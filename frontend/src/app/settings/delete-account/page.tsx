'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Trash2, ChevronLeft } from 'lucide-react';
import { authAPI } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/Button';
import { Input } from '@/components/Input';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Alert } from '@/components/Alert';
import Link from 'next/link';

export default function DeleteAccountPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { user, logout, setAccountDeleted } = useAuthStore();

  const [step, setStep] = useState(1);
  const [password, setPassword] = useState('');
  const [confirmText, setConfirmText] = useState('');
  const [deleteContent, setDeleteContent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletionComplete, setDeletionComplete] = useState(false);

  // Redirect if not logged in (but not after successful deletion)
  useEffect(() => {
    if (!user && !deletionComplete) {
      router.push('/signin?redirect=/settings/delete-account');
    }
  }, [user, router, deletionComplete]);

  // Don't render if not logged in (unless deletion just completed)
  if (!user && !deletionComplete) return null;

  const confirmPhrase = t('settings.delete.confirmPhrase');

  const handleDelete = async () => {
    if (confirmText.toUpperCase() !== confirmPhrase.toUpperCase()) {
      setError(t('settings.delete.confirmError', { phrase: confirmPhrase }));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await authAPI.deleteAccount({
        password,
        confirmation_text: confirmText,
        delete_content: deleteContent,
      });

      // Mark deletion as complete to prevent redirect to signin
      setDeletionComplete(true);

      // Set account deleted flag (for confirmation message on homepage)
      // Use both Zustand store and sessionStorage for reliability across navigation
      setAccountDeleted();
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('accountDeleted', 'true');
      }
      logout();
      router.push('/');
    } catch (err: unknown) {
      const axiosError = err as { response?: { status?: number } };
      if (axiosError.response?.status === 401) {
        setError(t('settings.delete.wrongPassword'));
      } else {
        setError(t('settings.delete.error'));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer maxWidth="2xl" paddingY="normal">
      <div className="mb-6">
        <Link
          href="/profile"
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          {t('common.back')}
        </Link>
      </div>

      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <PageHeader
          title={
            <span className="flex items-center gap-2 text-red-900 dark:text-red-300">
              <AlertTriangle className="w-6 h-6" />
              {t('settings.delete.title')}
            </span>
          }
        />

        <p className="text-red-800 dark:text-red-300 mb-6">{t('settings.delete.warning')}</p>

        {step === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
                {t('settings.delete.step1Title')}
              </h2>
              <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">
                {t('settings.delete.step1Description')}
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 space-y-4">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="deleteOption"
                  checked={!deleteContent}
                  onChange={() => setDeleteContent(false)}
                  className="mt-1"
                />
                <div>
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {t('settings.delete.optionAnonymize')}
                  </span>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {t('settings.delete.optionAnonymizeDesc')}
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="deleteOption"
                  checked={deleteContent}
                  onChange={() => setDeleteContent(true)}
                  className="mt-1"
                />
                <div>
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {t('settings.delete.optionDelete')}
                  </span>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {t('settings.delete.optionDeleteDesc')}
                  </p>
                </div>
              </label>
            </div>

            <Button onClick={() => setStep(2)} variant="danger">
              {t('settings.delete.continue')}
            </Button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
                {t('settings.delete.step2Title')}
              </h2>
            </div>

            <div className="space-y-4">
              <Input
                type="password"
                label={t('settings.delete.passwordLabel')}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('settings.delete.passwordPlaceholder')}
              />

              <div>
                <Input
                  type="text"
                  label={t('settings.delete.confirmLabel', { phrase: confirmPhrase })}
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder={confirmPhrase}
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {t('settings.delete.confirmHint', { phrase: confirmPhrase })}
                </p>
              </div>
            </div>

            {error && (
              <Alert variant="error" dismissible onDismiss={() => setError(null)}>
                {error}
              </Alert>
            )}

            <div className="flex gap-3">
              <Button onClick={() => setStep(1)} variant="secondary" disabled={loading}>
                {t('common.back')}
              </Button>
              <Button
                onClick={handleDelete}
                variant="danger"
                disabled={loading || !password || !confirmText}
                loading={loading}
                className="flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                {t('settings.delete.confirm')}
              </Button>
            </div>
          </div>
        )}
      </div>

      <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {t('settings.delete.law25Notice')}
        </p>
      </div>
    </PageContainer>
  );
}
