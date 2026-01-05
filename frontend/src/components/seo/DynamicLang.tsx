'use client';

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

/**
 * Updates the HTML lang attribute based on current i18n language.
 * This ensures the lang attribute reflects the actual content language.
 */
export function DynamicLang() {
  const { i18n } = useTranslation();

  useEffect(() => {
    // Map i18n language codes to HTML lang codes
    const langMap: Record<string, string> = {
      fr: 'fr-CA',
      en: 'en-CA',
    };

    const htmlLang = langMap[i18n.language] || i18n.language;

    // Update the HTML lang attribute
    if (document.documentElement.lang !== htmlLang) {
      document.documentElement.lang = htmlLang;
    }
  }, [i18n.language]);

  return null;
}
