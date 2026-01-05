'use client';

import { useTranslation } from 'react-i18next';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';

interface ThemeToggleProps {
  className?: string;
}

export function ThemeToggle({ className = '' }: ThemeToggleProps) {
  const { t } = useTranslation();
  const { isDark, toggleTheme, mounted } = useTheme();

  // Avoid hydration mismatch by not rendering until mounted
  if (!mounted) {
    return (
      <button
        className={`p-2 rounded-lg text-gray-500 ${className}`}
        aria-label={t('theme.switchToDark')}
        disabled
      >
        <Moon className="w-5 h-5" aria-hidden="true" />
      </button>
    );
  }

  return (
    <button
      onClick={toggleTheme}
      aria-label={isDark ? t('theme.switchToLight') : t('theme.switchToDark')}
      aria-pressed={isDark}
      className={`p-2 rounded-lg transition-colors duration-150
                 hover:bg-gray-100 dark:hover:bg-gray-800
                 text-gray-700 dark:text-gray-200
                 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
                 ${className}`}
    >
      {isDark ? (
        <Sun className="w-5 h-5" aria-hidden="true" />
      ) : (
        <Moon className="w-5 h-5" aria-hidden="true" />
      )}
    </button>
  );
}

export default ThemeToggle;
