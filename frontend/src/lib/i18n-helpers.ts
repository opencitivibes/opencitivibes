/**
 * Centralized i18n helper utilities.
 *
 * This module provides locale-aware helpers that support all languages
 * instead of hardcoding FR/EN checks.
 */

import { fr, enUS, es } from 'date-fns/locale';
import type { Locale } from 'date-fns';

/**
 * Supported locale codes for the application.
 */
export type SupportedLocale = 'fr' | 'en' | 'es';

/**
 * Get the Intl locale code for date formatting.
 * Maps our app locales to proper Intl locale codes.
 */
export function getIntlLocaleCode(lang: string): string {
  const localeMap: Record<string, string> = {
    fr: 'fr-CA',
    en: 'en-CA',
    es: 'es-ES',
  };
  return localeMap[lang] || 'en-CA';
}

/**
 * Get the date-fns locale object for the given language.
 */
export function getDateFnsLocale(lang: string): Locale {
  const localeMap: Record<string, Locale> = {
    fr: fr,
    en: enUS,
    es: es,
  };
  return localeMap[lang] || enUS;
}

/**
 * Get a localized field from an object with _fr/_en/_es suffixes.
 * Falls back to English if the requested locale is not available.
 *
 * @example
 * const name = getLocalizedValue(category, 'name', 'fr'); // returns category.name_fr
 */
export function getLocalizedValue<T extends Record<string, unknown>>(
  obj: T | null | undefined,
  fieldPrefix: string,
  locale: string,
  fallback: string = ''
): string {
  if (!obj) return fallback;

  const localeKey = `${fieldPrefix}_${locale}`;
  const fallbackKey = `${fieldPrefix}_en`;

  return (obj[localeKey] as string) || (obj[fallbackKey] as string) || fallback;
}

/**
 * Get all supported Intl locale codes for structured data/SEO.
 */
export function getSupportedIntlLocales(): string[] {
  return ['fr-CA', 'en-CA', 'es-ES'];
}

/**
 * Get all supported app locales.
 */
export function getSupportedLocales(): SupportedLocale[] {
  return ['fr', 'en', 'es'];
}

/**
 * Check if a locale is supported.
 */
export function isSupportedLocale(locale: string): locale is SupportedLocale {
  return ['fr', 'en', 'es'].includes(locale);
}
