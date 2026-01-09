'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronUp, Smartphone, Info, ExternalLink } from 'lucide-react';
import Link from 'next/link';

interface DeviceTrustConsentProps {
  onConsentChange: (consented: boolean) => void;
  disabled?: boolean;
}

/**
 * Law 25 Compliant Device Trust Consent Component
 *
 * Displays full disclosure about device trust data collection BEFORE
 * the user can consent to trusting their device. Checkbox is unchecked
 * by default (opt-in requirement).
 */
export function DeviceTrustConsent({ onConsentChange, disabled = false }: DeviceTrustConsentProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const [consented, setConsented] = useState(false);

  const handleConsentChange = (checked: boolean) => {
    setConsented(checked);
    onConsentChange(checked);
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      {/* Header - collapsible */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        disabled={disabled}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <Smartphone className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-gray-100">
              {t('security.devices.consent.heading')}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {t('security.devices.consent.optional')}
            </p>
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        )}
      </button>

      {/* Expanded content - Law 25 disclosure */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-200 dark:border-gray-700 pt-4">
          {/* What we collect */}
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {t('security.devices.consent.whatWeCollect')}
              </p>
            </div>
          </div>

          {/* Why we collect it */}
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t('security.devices.consent.why')}
            </p>
          </div>

          {/* Duration */}
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t('security.devices.consent.duration')}
            </p>
          </div>

          {/* Your rights */}
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t('security.devices.consent.yourRights')}
            </p>
          </div>

          {/* Data retention */}
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t('security.devices.consent.dataRetention')}
            </p>
          </div>

          {/* Privacy policy link */}
          <div className="flex items-center gap-2 text-sm">
            <Link
              href="/privacy"
              target="_blank"
              className="text-primary-600 hover:text-primary-700 dark:text-primary-400 flex items-center gap-1"
            >
              {t('security.devices.consent.privacyLink')}
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>

          {/* Consent checkbox - UNCHECKED by default (Law 25 opt-in) */}
          <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={consented}
                onChange={(e) => handleConsentChange(e.target.checked)}
                disabled={disabled}
                className="mt-1 h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500 disabled:opacity-50"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {t('security.devices.consent.checkbox')}
              </span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
}
