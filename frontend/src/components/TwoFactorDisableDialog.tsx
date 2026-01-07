'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ShieldOff, AlertTriangle } from 'lucide-react';
import { authAPI } from '@/lib/api';
import { Button } from '@/components/Button';
import { Alert } from '@/components/Alert';
import { Input } from '@/components/Input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';

interface TwoFactorDisableDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function TwoFactorDisableDialog({
  open,
  onOpenChange,
  onSuccess,
}: TwoFactorDisableDialogProps) {
  const { t } = useTranslation();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleDisable = async () => {
    if (!password) {
      setError(t('twoFactor.passwordRequired'));
      return;
    }

    setLoading(true);
    setError('');

    try {
      await authAPI.disable2FA({ password });
      onSuccess();
      onOpenChange(false);
      setPassword('');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || t('twoFactor.disableError'));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setPassword('');
    setError('');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
              <ShieldOff className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <DialogTitle>{t('twoFactor.disableTitle')}</DialogTitle>
              <DialogDescription>{t('twoFactor.disableDescription')}</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <Alert variant="warning">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
              <p className="text-sm">{t('twoFactor.disableWarning')}</p>
            </div>
          </Alert>

          <Input
            type="password"
            label={t('auth.password')}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="********"
            autoComplete="current-password"
          />

          {error && (
            <Alert variant="error" dismissible onDismiss={() => setError('')}>
              {error}
            </Alert>
          )}
        </div>

        <div className="flex gap-3">
          <Button variant="secondary" onClick={handleClose} className="flex-1">
            {t('common.cancel')}
          </Button>
          <Button
            variant="danger"
            onClick={handleDisable}
            disabled={!password || loading}
            loading={loading}
            className="flex-1"
          >
            {t('twoFactor.disable')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
