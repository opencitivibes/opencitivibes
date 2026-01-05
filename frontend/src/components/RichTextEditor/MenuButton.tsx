'use client';

import type { ToolbarButtonProps } from '@/types/editor';

export function MenuButton({
  children,
  isActive = false,
  onClick,
  title,
  disabled = false,
}: ToolbarButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-label={title}
      aria-pressed={isActive}
      tabIndex={0}
      className={`
        p-1.5 sm:p-2 min-w-[36px] sm:min-w-[44px] min-h-[36px] sm:min-h-[44px] rounded
        flex items-center justify-center
        transition-colors duration-150
        focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1 dark:ring-offset-gray-800
        focus-visible:ring-2 focus-visible:ring-primary-500
        ${
          disabled
            ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
            : isActive
              ? 'bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/50'
              : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 hover:text-gray-900 dark:hover:text-gray-100'
        }
      `}
    >
      {children}
    </button>
  );
}

/**
 * Toolbar divider for visual grouping
 */
export function MenuDivider() {
  return (
    <div
      className="w-px h-5 sm:h-6 bg-gray-300 dark:bg-gray-600 mx-0.5 sm:mx-1"
      aria-hidden="true"
    />
  );
}
