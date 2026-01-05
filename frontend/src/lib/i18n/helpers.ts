/**
 * i18n helper functions for dynamic content and configuration-aware translations.
 */

import type { TFunction } from 'i18next';
import type { PlatformConfig } from '@/lib/config/PlatformConfigProvider';

/**
 * Get localized value from a locale map.
 * Falls back through: current locale -> default locale -> first available -> fallback
 */
export function getLocalizedValue(
  localeMap: Record<string, string> | undefined,
  currentLocale: string,
  defaultLocale: string = 'en',
  fallback: string = ''
): string {
  if (!localeMap) return fallback;

  const keys = Object.keys(localeMap);
  const firstKey = keys.length > 0 ? keys[0] : undefined;

  return (
    localeMap[currentLocale] ||
    localeMap[defaultLocale] ||
    (firstKey ? localeMap[firstKey] : undefined) ||
    fallback
  );
}

/**
 * Get bilingual field (name_en/name_fr pattern common in API responses).
 */
export function getBilingualField<T extends Record<string, unknown>>(
  obj: T,
  fieldPrefix: string,
  locale: string
): string {
  const key = `${fieldPrefix}_${locale}` as keyof T;
  const fallbackKey = `${fieldPrefix}_en` as keyof T;

  return ((obj[key] as string) || (obj[fallbackKey] as string) || '') as string;
}

/**
 * Interpolate platform config values into translation strings.
 *
 * Replaces {{config.xxx}} placeholders with actual config values.
 */
export function interpolateConfig(text: string, config: PlatformConfig, locale: string): string {
  const replacements: Record<string, string> = {
    'config.instanceName': getLocalizedValue(config.instance.name, locale),
    'config.entityName': getLocalizedValue(config.instance.entity.name, locale),
    'config.location': config.instance.location
      ? getLocalizedValue(config.instance.location.display, locale)
      : '',
    'config.contactEmail': config.contact.email,
    'config.jurisdiction': config.legal ? getLocalizedValue(config.legal.jurisdiction, locale) : '',
  };

  let result = text;
  for (const [key, value] of Object.entries(replacements)) {
    result = result.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), value);
  }

  return result;
}

/**
 * Create a translation function that automatically interpolates config values.
 */
export function createConfigAwareT(t: TFunction, config: PlatformConfig | null, locale: string) {
  return (key: string, options?: Record<string, unknown>): string => {
    const translated = String(t(key, options as never));
    if (!config) return translated;
    return interpolateConfig(translated, config, locale);
  };
}
