'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Smartphone, Laptop, Globe, Clock, Pencil, Trash2, Check, X, Star } from 'lucide-react';
import { Button } from '@/components/Button';
import type { TrustedDevice } from '@/types';

interface TrustedDeviceCardProps {
  device: TrustedDevice;
  isCurrentDevice?: boolean;
  onRename: (deviceId: number, newName: string) => Promise<void>;
  onRevoke: (device: TrustedDevice) => void;
}

/**
 * Format date for display based on current locale
 */
function formatDate(dateString: string, locale: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString(locale === 'fr' ? 'fr-CA' : 'en-CA', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Get device icon based on platform info
 */
function getDeviceIcon(platform?: string) {
  if (!platform) return Smartphone;
  const p = platform.toLowerCase();
  if (p.includes('mobile') || p.includes('iphone') || p.includes('android')) {
    return Smartphone;
  }
  return Laptop;
}

export function TrustedDeviceCard({
  device,
  isCurrentDevice = false,
  onRename,
  onRevoke,
}: TrustedDeviceCardProps) {
  const { t, i18n } = useTranslation();
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(device.device_name);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const DeviceIcon = getDeviceIcon(device.fingerprint?.platform);
  const isExpired = new Date(device.expires_at) <= new Date();

  const handleSaveRename = async () => {
    if (!editName.trim() || editName === device.device_name) {
      setIsEditing(false);
      setEditName(device.device_name);
      return;
    }

    setIsSubmitting(true);
    try {
      await onRename(device.id, editName.trim());
      setIsEditing(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditName(device.device_name);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveRename();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  return (
    <div
      className={`p-4 border rounded-lg ${
        isExpired
          ? 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10'
          : isCurrentDevice
            ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/10'
            : 'border-gray-200 dark:border-gray-700'
      }`}
    >
      <div className="flex items-start gap-4">
        {/* Device icon */}
        <div
          className={`p-2.5 rounded-lg ${
            isExpired
              ? 'bg-red-100 dark:bg-red-900/30'
              : isCurrentDevice
                ? 'bg-green-100 dark:bg-green-900/30'
                : 'bg-gray-100 dark:bg-gray-800'
          }`}
        >
          <DeviceIcon
            className={`w-6 h-6 ${
              isExpired
                ? 'text-red-600 dark:text-red-400'
                : isCurrentDevice
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-gray-500 dark:text-gray-400'
            }`}
          />
        </div>

        {/* Device info */}
        <div className="flex-1 min-w-0">
          {/* Name row with edit capability */}
          <div className="flex items-center gap-2">
            {isEditing ? (
              <div className="flex items-center gap-2 flex-1">
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={handleKeyDown}
                  maxLength={100}
                  className="flex-1 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  autoFocus
                  disabled={isSubmitting}
                />
                <button
                  onClick={handleSaveRename}
                  disabled={isSubmitting}
                  className="p-1 text-green-600 hover:text-green-700 dark:text-green-400 disabled:opacity-50"
                  aria-label={t('common.save')}
                >
                  <Check className="w-4 h-4" />
                </button>
                <button
                  onClick={handleCancelEdit}
                  disabled={isSubmitting}
                  className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 disabled:opacity-50"
                  aria-label={t('common.cancel')}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <>
                <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                  {device.device_name}
                </h3>
                {isCurrentDevice && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full">
                    <Star className="w-3 h-3" />
                    {t('security.devices.current')}
                  </span>
                )}
                {isExpired && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-full">
                    {t('security.devices.expired')}
                  </span>
                )}
              </>
            )}
          </div>

          {/* Device details */}
          <div className="mt-1 space-y-1 text-sm text-gray-500 dark:text-gray-400">
            {/* Browser/OS info */}
            {device.fingerprint && (device.fingerprint.browser || device.fingerprint.os) && (
              <div className="flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5" />
                <span>
                  {[device.fingerprint.browser, device.fingerprint.os].filter(Boolean).join(' • ')}
                </span>
              </div>
            )}

            {/* Dates */}
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              <span>
                {t('security.devices.trustedOn', {
                  date: formatDate(device.trusted_at, i18n.language),
                })}
              </span>
            </div>

            {device.last_used_at && (
              <div className="flex items-center gap-1.5 ml-5">
                <span className="text-xs">
                  {t('security.devices.lastUsed', {
                    date: formatDate(device.last_used_at, i18n.language),
                  })}
                </span>
              </div>
            )}

            <div className="flex items-center gap-1.5 ml-5">
              <span className={`text-xs ${isExpired ? 'text-red-500 dark:text-red-400' : ''}`}>
                {isExpired
                  ? t('security.devices.expiredOn', {
                      date: formatDate(device.expires_at, i18n.language),
                    })
                  : t('security.devices.expiresOn', {
                      date: formatDate(device.expires_at, i18n.language),
                    })}
              </span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1">
          {!isEditing && (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsEditing(true)}
                className="p-2"
                aria-label={t('security.devices.rename')}
              >
                <Pencil className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onRevoke(device)}
                className="p-2 text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                aria-label={t('security.devices.revoke')}
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
