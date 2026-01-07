'use client';

import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Shield, Key } from 'lucide-react';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Alert } from '@/components/Alert';
import { Input } from '@/components/Input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

interface TwoFactorVerifyProps {
  email: string;
  onVerify: (code: string, isBackupCode: boolean) => Promise<void>;
  onCancel: () => void;
}

export function TwoFactorVerify({ email, onVerify, onCancel }: TwoFactorVerifyProps) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'totp' | 'backup'>('totp');
  const [code, setCode] = useState('');
  const [backupCode, setBackupCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, [activeTab]);

  const handleSubmit = async (isBackup: boolean) => {
    const codeToVerify = isBackup ? backupCode : code;
    if (!codeToVerify || (isBackup ? codeToVerify.length < 8 : codeToVerify.length !== 6)) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      await onVerify(codeToVerify, isBackup);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || t('twoFactor.invalidCode'));
    } finally {
      setLoading(false);
    }
  };

  const handleCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setCode(value);
  };

  const handleBackupCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '')
      .slice(0, 8);
    setBackupCode(value);
  };

  const handleKeyDown = (e: React.KeyboardEvent, isBackup: boolean) => {
    if (e.key === 'Enter') {
      handleSubmit(isBackup);
    }
  };

  return (
    <Card className="max-w-md mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
          <Shield className="w-6 h-6 text-primary-600 dark:text-primary-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            {t('twoFactor.verifyTitle')}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">{email}</p>
        </div>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as 'totp' | 'backup')}
        className="w-full"
      >
        <TabsList className="grid w-full grid-cols-2 mb-6">
          <TabsTrigger value="totp" className="flex items-center gap-2">
            <Shield className="w-4 h-4" />
            {t('twoFactor.authenticatorApp')}
          </TabsTrigger>
          <TabsTrigger value="backup" className="flex items-center gap-2">
            <Key className="w-4 h-4" />
            {t('twoFactor.backupCode')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="totp" className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {t('twoFactor.enterCodeFromApp')}
          </p>

          <Input
            ref={inputRef}
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={handleCodeChange}
            onKeyDown={(e) => handleKeyDown(e, false)}
            placeholder="000000"
            className="text-center text-2xl tracking-[0.5em] font-mono"
          />

          {error && (
            <Alert variant="error" dismissible onDismiss={() => setError('')}>
              {error}
            </Alert>
          )}

          <Button
            variant="primary"
            onClick={() => handleSubmit(false)}
            disabled={code.length !== 6 || loading}
            loading={loading}
            className="w-full"
          >
            {t('twoFactor.verify')}
          </Button>
        </TabsContent>

        <TabsContent value="backup" className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {t('twoFactor.enterBackupCode')}
          </p>

          <Input
            ref={activeTab === 'backup' ? inputRef : undefined}
            type="text"
            maxLength={8}
            value={backupCode}
            onChange={handleBackupCodeChange}
            onKeyDown={(e) => handleKeyDown(e, true)}
            placeholder="XXXXXXXX"
            className="text-center text-xl tracking-[0.3em] font-mono uppercase"
          />

          {error && (
            <Alert variant="error" dismissible onDismiss={() => setError('')}>
              {error}
            </Alert>
          )}

          <Button
            variant="primary"
            onClick={() => handleSubmit(true)}
            disabled={backupCode.length < 8 || loading}
            loading={loading}
            className="w-full"
          >
            {t('twoFactor.verify')}
          </Button>
        </TabsContent>
      </Tabs>

      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <Button variant="ghost" onClick={onCancel} className="w-full">
          {t('common.cancel')}
        </Button>
      </div>
    </Card>
  );
}
