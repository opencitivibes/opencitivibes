/**
 * Translation hook that automatically interpolates platform configuration.
 */

import { useTranslation } from 'react-i18next';
import { usePlatformConfig } from '@/lib/config/PlatformConfigProvider';
import { useCallback, useMemo } from 'react';
import { interpolateConfig } from '@/lib/i18n/helpers';

/**
 * Enhanced translation hook with config interpolation.
 *
 * Usage:
 * ```tsx
 * const { t, tc } = useConfigTranslation();
 *
 * // Regular translation
 * t('common.save')
 *
 * // Translation with config interpolation
 * tc('app.title') // "Ideas for Montreal" (from config)
 * ```
 */
export function useConfigTranslation() {
  const { t, i18n } = useTranslation();
  const { config } = usePlatformConfig();

  /**
   * Translate with config value interpolation.
   * Replaces {{config.xxx}} placeholders with actual values.
   */
  const tc = useCallback(
    (key: string, options?: Record<string, unknown>): string => {
      const translated = String(t(key, options as never));
      if (!config) return translated;
      return interpolateConfig(translated, config, i18n.language);
    },
    [t, config, i18n.language]
  );

  /**
   * Get instance name in current locale.
   */
  const instanceName = useMemo(() => {
    if (!config) return 'OpenCitiVibes';
    return config.instance.name[i18n.language] || config.instance.name['en'] || 'OpenCitiVibes';
  }, [config, i18n.language]);

  /**
   * Get entity name in current locale.
   */
  const entityName = useMemo(() => {
    if (!config) return '';
    return config.instance.entity.name[i18n.language] || config.instance.entity.name['en'] || '';
  }, [config, i18n.language]);

  /**
   * Get localized value from a Record<string, string> object.
   */
  const getLocalizedValue = useCallback(
    (obj: Record<string, string> | undefined, fallback = ''): string => {
      if (!obj) return fallback;
      const keys = Object.keys(obj);
      const firstKey = keys.length > 0 ? keys[0] : undefined;
      return obj[i18n.language] || obj['en'] || (firstKey ? obj[firstKey] : undefined) || fallback;
    },
    [i18n.language]
  );

  return {
    t, // Regular translation
    tc, // Config-aware translation
    i18n,
    instanceName,
    entityName,
    config,
    getLocalizedValue, // Get localized value from a Record<string, string>
  };
}
