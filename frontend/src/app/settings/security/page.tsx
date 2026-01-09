'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import Link from 'next/link';
import {
  ChevronLeft,
  Shield,
  ShieldCheck,
  ShieldOff,
  Key,
  RefreshCw,
  AlertTriangle,
  Smartphone,
  ChevronRight,
} from 'lucide-react';
import { authAPI } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Alert } from '@/components/Alert';
import { TwoFactorSetup } from '@/components/TwoFactorSetup';
import { TwoFactorDisableDialog } from '@/components/TwoFactorDisableDialog';
import { useToast } from '@/hooks/useToast';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import type { TwoFactorStatusResponse } from '@/types';

export default function SecuritySettingsPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { user } = useAuthStore();
  const { success, error: showError } = useToast();

  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<TwoFactorStatusResponse | null>(null);
  const [showSetup, setShowSetup] = useState(false);
  const [showDisable, setShowDisable] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  // Redirect if not logged in
  useEffect(() => {
    if (!user) {
      router.push('/signin?redirect=/settings/security');
    }
  }, [user, router]);

  // Fetch 2FA status
  const fetchStatus = async () => {
    try {
      setLoading(true);
      const response = await authAPI.get2FAStatus();
      setStatus(response);
    } catch {
      showError(t('twoFactor.statusError'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchStatus();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const handleSetupComplete = () => {
    setShowSetup(false);
    success(t('twoFactor.enabledSuccess'));
    fetchStatus();
  };

  const handleDisableSuccess = () => {
    success(t('twoFactor.disabledSuccess'));
    fetchStatus();
  };

  const handleRegenerateBackupCodes = async () => {
    const password = prompt(t('twoFactor.enterPasswordToRegenerate'));
    if (!password) return;

    setRegenerating(true);
    try {
      const response = await authAPI.regenerateBackupCodes({ password });
      // Show backup codes in alert
      alert(t('twoFactor.newBackupCodes') + '\n\n' + response.backup_codes.join('\n'));
      success(t('twoFactor.backupCodesRegenerated'));
      fetchStatus();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      showError(axiosError.response?.data?.detail || t('twoFactor.regenerateError'));
    } finally {
      setRegenerating(false);
    }
  };

  if (!user) return null;

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

      <PageHeader
        title={t('settings.security.title')}
        description={t('settings.security.description')}
      />

      {loading ? (
        <Card className="mt-6 animate-pulse">
          <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded" />
        </Card>
      ) : (
        <>
          {/* 2FA Status Card */}
          <Card className="mt-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                {status?.enabled ? (
                  <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                    <ShieldCheck className="w-6 h-6 text-green-600 dark:text-green-400" />
                  </div>
                ) : (
                  <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                    <Shield className="w-6 h-6 text-gray-500 dark:text-gray-400" />
                  </div>
                )}
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {t('twoFactor.title')}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {status?.enabled ? t('twoFactor.enabled') : t('twoFactor.disabled')}
                  </p>
                </div>
              </div>

              {status?.enabled ? (
                <Button
                  variant="secondary"
                  onClick={() => setShowDisable(true)}
                  className="shrink-0"
                >
                  <ShieldOff className="w-4 h-4 mr-2" />
                  {t('twoFactor.disable')}
                </Button>
              ) : (
                <Button variant="primary" onClick={() => setShowSetup(true)} className="shrink-0">
                  <Shield className="w-4 h-4 mr-2" />
                  {t('twoFactor.enable')}
                </Button>
              )}
            </div>

            {status?.enabled && (
              <>
                {/* Backup Codes Section */}
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Key className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="font-medium text-gray-900 dark:text-gray-100">
                          {t('twoFactor.backupCodes')}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {t('twoFactor.backupCodesRemaining', {
                            count: status.backup_codes_remaining,
                          })}
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleRegenerateBackupCodes}
                      loading={regenerating}
                      disabled={regenerating}
                    >
                      <RefreshCw className="w-4 h-4 mr-2" />
                      {t('twoFactor.regenerate')}
                    </Button>
                  </div>

                  {status.backup_codes_remaining <= 2 && (
                    <Alert variant="warning" className="mt-4">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                        <p>
                          {t('twoFactor.lowBackupCodesWarning', {
                            count: status.backup_codes_remaining,
                          })}
                        </p>
                      </div>
                    </Alert>
                  )}
                </div>
              </>
            )}
          </Card>

          {/* Trusted Devices Section (only show if 2FA enabled) */}
          {status?.enabled && (
            <Card className="mt-6">
              <Link
                href="/settings/devices"
                className="flex items-center justify-between p-0 hover:bg-gray-50 dark:hover:bg-gray-800/50 -m-4 p-4 rounded-lg transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                    <Smartphone className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      {t('security.devices.sectionTitle')}
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {t('security.devices.sectionDescription')}
                    </p>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </Link>
            </Card>
          )}

          {/* Info about 2FA */}
          <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
            <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
              {t('twoFactor.whatIs2FA')}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t('twoFactor.whatIs2FADescription')}
            </p>
          </div>

          {/* Links to other settings */}
          <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700 flex gap-4">
            <Link
              href="/settings/consent"
              className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400"
            >
              {t('settings.consent.title')}
            </Link>
            <Link
              href="/settings/data"
              className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400"
            >
              {t('settings.data.title')}
            </Link>
            <Link
              href="/settings/delete-account"
              className="text-sm text-red-600 hover:text-red-700 dark:text-red-400"
            >
              {t('settings.delete.title')}
            </Link>
          </div>
        </>
      )}

      {/* Setup Dialog */}
      <Dialog open={showSetup} onOpenChange={setShowSetup}>
        <DialogContent className="sm:max-w-md p-0 gap-0 border-0 bg-transparent shadow-none">
          <TwoFactorSetup onComplete={handleSetupComplete} onCancel={() => setShowSetup(false)} />
        </DialogContent>
      </Dialog>

      {/* Disable Dialog */}
      <TwoFactorDisableDialog
        open={showDisable}
        onOpenChange={setShowDisable}
        onSuccess={handleDisableSuccess}
      />
    </PageContainer>
  );
}
