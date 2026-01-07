'use client';

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { QRCodeSVG } from 'qrcode.react';
import { Shield, Copy, Check, AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react';
import { authAPI } from '@/lib/api';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Alert } from '@/components/Alert';
import { Input } from '@/components/Input';

interface TwoFactorSetupProps {
  onComplete: () => void;
  onCancel: () => void;
}

type SetupStep = 'loading' | 'qr' | 'verify' | 'backup';

export function TwoFactorSetup({ onComplete, onCancel }: TwoFactorSetupProps) {
  const { t } = useTranslation();
  const [step, setStep] = useState<SetupStep>('loading');
  const [setupData, setSetupData] = useState<{ secret: string; provisioning_uri: string } | null>(
    null
  );
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [backupCodesCopied, setBackupCodesCopied] = useState(false);

  // Initialize setup on mount
  useEffect(() => {
    const initSetup = async () => {
      try {
        const response = await authAPI.setup2FA();
        setSetupData(response);
        setStep('qr');
      } catch (err: unknown) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        setError(axiosError.response?.data?.detail || t('twoFactor.setupError'));
        setStep('qr'); // Show error in UI
      }
    };
    initSetup();
  }, [t]);

  const handleVerify = async () => {
    if (code.length !== 6) return;

    setLoading(true);
    setError('');

    try {
      const response = await authAPI.verify2FASetup(code);
      setBackupCodes(response.backup_codes);
      setStep('backup');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || t('twoFactor.invalidCode'));
    } finally {
      setLoading(false);
    }
  };

  const copySecret = () => {
    if (setupData?.secret) {
      navigator.clipboard.writeText(setupData.secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const copyBackupCodes = () => {
    const codesText = backupCodes.join('\n');
    navigator.clipboard.writeText(codesText);
    setBackupCodesCopied(true);
    setTimeout(() => setBackupCodesCopied(false), 2000);
  };

  const handleCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setCode(value);
  };

  if (step === 'loading') {
    return (
      <Card className="max-w-md mx-auto">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      </Card>
    );
  }

  return (
    <Card className="max-w-md mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
          <Shield className="w-6 h-6 text-primary-600 dark:text-primary-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            {t('twoFactor.setupTitle')}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t('twoFactor.setupDescription')}
          </p>
        </div>
      </div>

      {error && !setupData && (
        <Alert variant="error" className="mb-4" dismissible onDismiss={() => setError('')}>
          {error}
        </Alert>
      )}

      {step === 'qr' && setupData && (
        <div className="space-y-6">
          <div className="text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              {t('twoFactor.scanQRCode')}
            </p>
            <div className="inline-block p-4 bg-white rounded-xl shadow-inner">
              <QRCodeSVG value={setupData.provisioning_uri} size={180} />
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              {t('twoFactor.orEnterManually')}
            </p>
            <div className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
              <code className="flex-1 text-xs font-mono text-gray-700 dark:text-gray-300 break-all select-all">
                {setupData.secret}
              </code>
              <Button variant="ghost" size="sm" onClick={copySecret} className="shrink-0">
                {copied ? (
                  <Check className="w-4 h-4 text-green-500" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>

          <div className="flex gap-3">
            <Button variant="secondary" onClick={onCancel} className="flex-1">
              {t('common.cancel')}
            </Button>
            <Button variant="primary" onClick={() => setStep('verify')} className="flex-1">
              {t('common.next')}
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>
      )}

      {step === 'verify' && (
        <div className="space-y-6">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {t('twoFactor.enterCodeFromApp')}
          </p>

          <div>
            <Input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={handleCodeChange}
              placeholder="000000"
              className="text-center text-2xl tracking-[0.5em] font-mono"
              autoFocus
            />
          </div>

          {error && (
            <Alert variant="error" dismissible onDismiss={() => setError('')}>
              {error}
            </Alert>
          )}

          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => {
                setStep('qr');
                setError('');
                setCode('');
              }}
              className="flex-1"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              {t('common.back')}
            </Button>
            <Button
              variant="primary"
              onClick={handleVerify}
              disabled={code.length !== 6 || loading}
              loading={loading}
              className="flex-1"
            >
              {t('twoFactor.verify')}
            </Button>
          </div>
        </div>
      )}

      {step === 'backup' && (
        <div className="space-y-6">
          <Alert variant="warning">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
              <p>{t('twoFactor.saveBackupCodes')}</p>
            </div>
          </Alert>

          <div className="grid grid-cols-2 gap-2 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
            {backupCodes.map((backupCode, i) => (
              <div
                key={i}
                className="font-mono text-sm text-gray-700 dark:text-gray-300 p-2 bg-white dark:bg-gray-900 rounded border border-gray-100 dark:border-gray-700 text-center"
              >
                {backupCode}
              </div>
            ))}
          </div>

          <Button variant="secondary" onClick={copyBackupCodes} className="w-full">
            {backupCodesCopied ? (
              <>
                <Check className="w-4 h-4 mr-2 text-green-500" />
                {t('twoFactor.copied')}
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 mr-2" />
                {t('twoFactor.copyBackupCodes')}
              </>
            )}
          </Button>

          <Button variant="primary" onClick={onComplete} className="w-full">
            {t('twoFactor.setupComplete')}
          </Button>
        </div>
      )}
    </Card>
  );
}
