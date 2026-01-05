'use client';

import { useTranslation } from 'react-i18next';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { usePlatformConfig } from '@/lib/config/PlatformConfigProvider';

const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English',
  fr: 'Francais',
  es: 'Espanol',
  de: 'Deutsch',
  it: 'Italiano',
  pt: 'Portugues',
  zh: '中文',
  ja: '日本語',
  ko: '한국어',
};

export function LanguageSelector() {
  const { i18n } = useTranslation();
  const { config } = usePlatformConfig();

  const supportedLocales = config?.localization?.supported_locales || ['fr', 'en'];
  const currentLang = i18n.language;

  const handleLanguageChange = (locale: string) => {
    i18n.changeLanguage(locale);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:ring-offset-gray-900 flex items-center gap-1"
        suppressHydrationWarning
      >
        <span className="uppercase">{currentLang}</span>
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[120px]">
        {supportedLocales.map((locale) => (
          <DropdownMenuItem
            key={locale}
            onClick={() => handleLanguageChange(locale)}
            className={`cursor-pointer ${
              currentLang === locale ? 'bg-primary-50 dark:bg-primary-900/30 font-medium' : ''
            }`}
          >
            <span className="uppercase mr-2 text-xs text-gray-500">{locale}</span>
            {LANGUAGE_NAMES[locale] || locale}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
