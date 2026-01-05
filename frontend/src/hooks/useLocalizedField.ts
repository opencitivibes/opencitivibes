/**
 * Hook for getting localized fields from API responses.
 *
 * Replaces the pattern: i18n.language === 'fr' ? obj.name_fr : obj.name_en
 */

import { useTranslation } from 'react-i18next';
import { useCallback } from 'react';
import { getIntlLocaleCode } from '@/lib/i18n-helpers';

// Backend stores this value when a user deletes their account
const DELETED_USER_MARKER = 'Deleted User';

interface LocalizableObject {
  [key: string]: unknown;
}

/**
 * Hook for accessing localized fields from objects with name_en/name_fr/name_es patterns.
 */
export function useLocalizedField() {
  const { i18n, t } = useTranslation();

  /**
   * Get a localized field value.
   *
   * @param obj Object containing localized fields
   * @param fieldPrefix Prefix of the field (e.g., 'name' for name_en/name_fr/name_es)
   * @param fallback Fallback value if field not found
   */
  const getField = useCallback(
    <T extends LocalizableObject>(
      obj: T | null | undefined,
      fieldPrefix: string,
      fallback: string = ''
    ): string => {
      if (!obj) return fallback;

      const locale = i18n.language;
      const localeKey = `${fieldPrefix}_${locale}`;
      const fallbackKey = `${fieldPrefix}_en`;

      return (obj[localeKey] as string) || (obj[fallbackKey] as string) || fallback;
    },
    [i18n.language]
  );

  /**
   * Get category name.
   * Handles both `name_` and `category_name_` prefixes.
   */
  const getCategoryName = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (category: any | null | undefined): string => {
      if (!category) return 'Unknown Category';
      // Try category_name_ prefix first (used in ideas), then name_ prefix (used in categories)
      const locale = i18n.language;
      return (
        category[`category_name_${locale}`] ||
        category[`category_name_en`] ||
        category[`name_${locale}`] ||
        category[`name_en`] ||
        'Unknown Category'
      );
    },
    [i18n.language]
  );

  /**
   * Get category description.
   * Handles both `description_` and `category_description_` prefixes.
   */
  const getCategoryDescription = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (category: any | null | undefined): string => {
      if (!category) return '';
      const locale = i18n.language;
      return (
        category[`category_description_${locale}`] ||
        category[`category_description_en`] ||
        category[`description_${locale}`] ||
        category[`description_en`] ||
        ''
      );
    },
    [i18n.language]
  );

  /**
   * Get quality name.
   */
  const getQualityName = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (quality: any | null | undefined): string => {
      if (!quality) return '';
      const locale = i18n.language;
      return quality[`quality_name_${locale}`] || quality[`quality_name_en`] || '';
    },
    [i18n.language]
  );

  /**
   * Format date according to current locale.
   */
  const formatDate = useCallback(
    (dateString: string | Date, options?: Intl.DateTimeFormatOptions): string => {
      const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
      const locale = getIntlLocaleCode(i18n.language);
      return date.toLocaleDateString(locale, options);
    },
    [i18n.language]
  );

  /**
   * Get display name with translation for deleted users.
   * Backend stores "Deleted User" when account is deleted.
   */
  const getDisplayName = useCallback(
    (displayName: string): string => {
      if (displayName === DELETED_USER_MARKER) {
        return t('common.deletedUser');
      }
      return displayName;
    },
    [t]
  );

  return {
    locale: i18n.language,
    getField,
    getCategoryName,
    getCategoryDescription,
    getQualityName,
    formatDate,
    getDisplayName,
  };
}
