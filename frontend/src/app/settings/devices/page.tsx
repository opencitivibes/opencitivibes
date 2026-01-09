'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import Link from 'next/link';
import { ChevronLeft, Smartphone, AlertTriangle, Info, Trash2 } from 'lucide-react';
import { authAPI } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Alert } from '@/components/Alert';
import { TrustedDeviceCard } from '@/components/TrustedDeviceCard';
import { RevokeDeviceDialog } from '@/components/RevokeDeviceDialog';
import { useToast } from '@/hooks/useToast';
import { getDeviceToken, getStoredDeviceId } from '@/lib/deviceToken';
import type { TrustedDevice, TrustedDeviceListResponse } from '@/types';

export default function TrustedDevicesPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { user } = useAuthStore();
  const { success, error: showError } = useToast();

  const [loading, setLoading] = useState(true);
  const [devices, setDevices] = useState<TrustedDevice[]>([]);
  const [totalDevices, setTotalDevices] = useState(0);
  const [revokeDialog, setRevokeDialog] = useState<{
    device: TrustedDevice | null;
    isCurrentDevice: boolean;
  }>({ device: null, isCurrentDevice: false });
  const [revokingAll, setRevokingAll] = useState(false);

  // Get current device token for comparison
  const currentDeviceToken = typeof window !== 'undefined' ? getDeviceToken() : null;

  // Redirect if not logged in
  useEffect(() => {
    if (!user) {
      router.push('/signin?redirect=/settings/devices');
    }
  }, [user, router]);

  // Fetch trusted devices
  const fetchDevices = useCallback(async () => {
    try {
      setLoading(true);
      const response: TrustedDeviceListResponse = await authAPI.getTrustedDevices();
      setDevices(response.devices);
      setTotalDevices(response.total);
    } catch {
      showError(t('security.devices.loadError'));
    } finally {
      setLoading(false);
    }
  }, [showError, t]);

  useEffect(() => {
    if (user) {
      fetchDevices();
    }
  }, [user, fetchDevices]);

  // Handle device rename
  const handleRename = async (deviceId: number, newName: string) => {
    try {
      await authAPI.renameDevice(deviceId, newName);
      success(t('security.devices.renamed'));
      fetchDevices();
    } catch {
      showError(t('security.devices.renameError'));
    }
  };

  // Handle single device revoke
  const handleRevokeConfirm = async (deviceId: number) => {
    try {
      await authAPI.revokeDevice(deviceId);
      success(t('security.devices.revoked'));
      setRevokeDialog({ device: null, isCurrentDevice: false });
      fetchDevices();
    } catch {
      showError(t('security.devices.revokeError'));
    }
  };

  // Handle revoke all devices
  const handleRevokeAll = async () => {
    if (!confirm(t('security.devices.revokeAllConfirm'))) return;

    setRevokingAll(true);
    try {
      const result = await authAPI.revokeAllDevices();
      success(t('security.devices.revokedAll', { count: result.count }));
      fetchDevices();
    } catch {
      showError(t('security.devices.revokeAllError'));
    } finally {
      setRevokingAll(false);
    }
  };

  // Get stored device ID for "current device" detection
  const storedDeviceId = getStoredDeviceId();

  // Check if a device is the current device by comparing stored device ID
  const isCurrentDevice = (device: TrustedDevice) => {
    return storedDeviceId !== null && device.id === storedDeviceId;
  };

  if (!user) return null;

  return (
    <PageContainer maxWidth="2xl" paddingY="normal">
      <div className="mb-6">
        <Link
          href="/settings/security"
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          {t('security.devices.backToSecurity')}
        </Link>
      </div>

      <PageHeader
        title={t('security.devices.title')}
        description={t('security.devices.description')}
      />

      {/* No device token warning */}
      {!currentDeviceToken && (
        <Alert variant="info" className="mt-6">
          <div className="flex items-start gap-2">
            <Info className="w-5 h-5 shrink-0 mt-0.5" />
            <p>{t('security.devices.noDeviceTokenInfo')}</p>
          </div>
        </Alert>
      )}

      {/* Devices list */}
      {loading ? (
        <Card className="mt-6 animate-pulse">
          <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded" />
        </Card>
      ) : devices.length === 0 ? (
        <Card className="mt-6">
          <div className="text-center py-12">
            <Smartphone className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              {t('security.devices.noDevices')}
            </h3>
            <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
              {t('security.devices.noDevicesDescription')}
            </p>
          </div>
        </Card>
      ) : (
        <>
          {/* Header with count and revoke all */}
          <div className="mt-6 flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {t('security.devices.count', { count: totalDevices })}
            </p>
            {devices.length > 1 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRevokeAll}
                loading={revokingAll}
                disabled={revokingAll}
                className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                {t('security.devices.revokeAll')}
              </Button>
            )}
          </div>

          {/* Device cards */}
          <div className="mt-4 space-y-3">
            {devices.map((device) => (
              <TrustedDeviceCard
                key={device.id}
                device={device}
                isCurrentDevice={isCurrentDevice(device)}
                onRename={handleRename}
                onRevoke={(d) =>
                  setRevokeDialog({
                    device: d,
                    isCurrentDevice: isCurrentDevice(d),
                  })
                }
              />
            ))}
          </div>
        </>
      )}

      {/* Law 25 info section */}
      <div className="mt-8 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
          {t('security.devices.law25Title')}
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
          {t('security.devices.law25Description')}
        </p>
        <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside">
          <li>{t('security.devices.law25Point1')}</li>
          <li>{t('security.devices.law25Point2')}</li>
          <li>{t('security.devices.law25Point3')}</li>
        </ul>
      </div>

      {/* Warning about security */}
      <Alert variant="warning" className="mt-6">
        <div className="flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">{t('security.devices.securityWarningTitle')}</p>
            <p className="mt-1">{t('security.devices.securityWarningText')}</p>
          </div>
        </div>
      </Alert>

      {/* Revoke dialog */}
      <RevokeDeviceDialog
        device={revokeDialog.device}
        open={revokeDialog.device !== null}
        onOpenChange={(open) => {
          if (!open) setRevokeDialog({ device: null, isCurrentDevice: false });
        }}
        onConfirm={handleRevokeConfirm}
        isCurrentDevice={revokeDialog.isCurrentDevice}
      />
    </PageContainer>
  );
}
