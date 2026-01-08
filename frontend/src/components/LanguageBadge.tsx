'use client';

import { useTranslation } from 'react-i18next';

type ContentLanguage = 'fr' | 'en' | 'es';

interface LanguageBadgeProps {
  language?: ContentLanguage;
  size?: 'sm' | 'md';
  className?: string;
}

/**
 * Visual indicator for content language (French/English/Spanish).
 * Uses distinct colors: blue for French, emerald for English, amber for Spanish.
 */
export function LanguageBadge({ language, size = 'sm', className = '' }: LanguageBadgeProps) {
  const { t } = useTranslation();

  // Default to French if undefined (backwards compat)
  const lang: ContentLanguage = language || 'fr';

  // Dynamic translation keys based on language
  const label = t(`language.badge.${lang}`, lang.toUpperCase());

  const ariaLabelMap: Record<ContentLanguage, string> = {
    fr: t('language.contentInFrench'),
    en: t('language.contentInEnglish'),
    es: t('language.contentInSpanish'),
  };

  const titleMap: Record<ContentLanguage, string> = {
    fr: t('language.french'),
    en: t('language.english'),
    es: t('language.spanish'),
  };

  const sizeClasses = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-sm px-2 py-1',
  };

  const colorClasses: Record<ContentLanguage, string> = {
    fr: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    en: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    es: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded ${colorClasses[lang]} ${sizeClasses[size]} ${className}`}
      title={titleMap[lang]}
      aria-label={ariaLabelMap[lang]}
    >
      {label}
    </span>
  );
}

export default LanguageBadge;
