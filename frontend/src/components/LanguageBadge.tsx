'use client';

import { useTranslation } from 'react-i18next';

interface LanguageBadgeProps {
  language?: 'fr' | 'en';
  size?: 'sm' | 'md';
  className?: string;
}

/**
 * Visual indicator for content language (French/English).
 * Uses distinct colors: blue for French, emerald for English.
 */
export function LanguageBadge({ language, size = 'sm', className = '' }: LanguageBadgeProps) {
  const { t } = useTranslation();

  // Default to French if undefined (backwards compat)
  const lang = language || 'fr';
  const label = lang === 'fr' ? t('language.badge.fr') : t('language.badge.en');
  const ariaLabel = lang === 'fr' ? t('language.contentInFrench') : t('language.contentInEnglish');

  const sizeClasses = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-sm px-2 py-1',
  };

  const colorClasses = {
    fr: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    en: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded ${colorClasses[lang]} ${sizeClasses[size]} ${className}`}
      title={lang === 'fr' ? t('language.french') : t('language.english')}
      aria-label={ariaLabel}
    >
      {label}
    </span>
  );
}

export default LanguageBadge;
