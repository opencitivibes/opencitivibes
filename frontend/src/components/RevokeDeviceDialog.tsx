'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Smartphone } from 'lucide-react';
import { Button } from '@/components/Button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { TrustedDevice } from '@/types';

interface RevokeDeviceDialogProps {
  device: TrustedDevice | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (deviceId: number) => Promise<void>;
  isCurrentDevice?: boolean;
}

export function RevokeDeviceDialog({
  device,
  open,
  onOpenChange,
  onConfirm,
  isCurrentDevice = false,
}: RevokeDeviceDialogProps) {
  const { t } = useTranslation();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleConfirm = async () => {
    if (!device) return;

    setIsSubmitting(true);
    try {
      await onConfirm(device.id);
      onOpenChange(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!device) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <DialogTitle>{t('security.devices.revokeTitle')}</DialogTitle>
              <DialogDescription className="mt-1">
                {isCurrentDevice
                  ? t('security.devices.revokeCurrentWarning')
                  : t('security.devices.revokeDescription')}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Device info summary */}
        <div className="my-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <div className="flex items-center gap-3">
            <Smartphone className="w-5 h-5 text-gray-500 dark:text-gray-400" />
            <div>
              <p className="font-medium text-gray-900 dark:text-gray-100">{device.device_name}</p>
              {device.fingerprint && (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {[device.fingerprint.browser, device.fingerprint.os].filter(Boolean).join(' • ')}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Warning for current device */}
        {isCurrentDevice && (
          <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              {t('security.devices.revokeCurrentExplanation')}
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 mt-4">
          <Button variant="secondary" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            {t('common.cancel')}
          </Button>
          <Button
            variant="primary"
            onClick={handleConfirm}
            loading={isSubmitting}
            disabled={isSubmitting}
            className="bg-red-600 hover:bg-red-700 focus:ring-red-500"
          >
            {t('security.devices.revokeConfirm')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
