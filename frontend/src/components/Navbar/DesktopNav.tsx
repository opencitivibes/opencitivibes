'use client';

import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { BarChart3 } from 'lucide-react';
import { User } from '@/types';
import { Button } from '../Button';
import { ThemeToggle } from '../ThemeToggle';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { AdminMenuItemsDesktop } from './AdminMenuItems';
import { UserAvatar } from './UserAvatar';
import { LanguageSelector } from './LanguageSelector';

interface DesktopNavProps {
  user: User | null;
  getNavLinkClass: (href: string) => string;
  logout: () => void;
  adminMenuOpen: boolean;
  setAdminMenuOpen: (open: boolean) => void;
}

export function DesktopNav({
  user,
  getNavLinkClass,
  logout,
  adminMenuOpen,
  setAdminMenuOpen,
}: DesktopNavProps) {
  const { t } = useTranslation();

  return (
    <div className="hidden md:flex items-center space-x-6" suppressHydrationWarning>
      <Link href="/" className={getNavLinkClass('/')} suppressHydrationWarning>
        {t('nav.home')}
      </Link>

      {user && (
        <>
          {/* Hide My Ideas and Submit for officials (non-admin) */}
          {(!user.is_official || user.is_global_admin) && (
            <>
              <Link
                href="/my-ideas"
                className={getNavLinkClass('/my-ideas')}
                suppressHydrationWarning
              >
                {t('nav.myIdeas')}
              </Link>
              <Link href="/submit" className={getNavLinkClass('/submit')} suppressHydrationWarning>
                {t('nav.submitIdea')}
              </Link>
            </>
          )}
          {user.is_official && !user.is_global_admin && (
            <Link
              href="/officials"
              className={`${getNavLinkClass('/officials')} flex items-center gap-1.5`}
            >
              <BarChart3 className="w-4 h-4" />
              {t('nav.officialDashboard')}
            </Link>
          )}
          {user.is_global_admin && (
            <DropdownMenu open={adminMenuOpen} onOpenChange={setAdminMenuOpen}>
              <DropdownMenuTrigger className="font-medium transition-colors duration-150 focus:outline-none pb-1 border-b-2 border-transparent text-gray-700 dark:text-gray-200 hover:text-primary-600 dark:hover:text-primary-400 data-[state=open]:text-primary-600 data-[state=open]:border-primary-500 dark:data-[state=open]:text-primary-400 flex items-center gap-1">
                {t('nav.adminPanel')}
                <svg
                  className="w-4 h-4 transition-transform duration-200"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <AdminMenuItemsDesktop onItemClick={() => setAdminMenuOpen(false)} />
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </>
      )}

      {/* Command Palette Shortcut */}
      <button
        onClick={() => {
          const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true, ctrlKey: true });
          document.dispatchEvent(event);
        }}
        className="hidden lg:flex items-center gap-1.5 px-2 py-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 rounded border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 transition-colors"
        title={t('commandPalette.searchPlaceholder', 'Type a command or search...')}
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <span className="text-xs">
          <kbd className="font-sans">⌘</kbd>K
        </span>
      </button>

      {/* Settings Cluster: Language + Theme */}
      <div className="flex items-center space-x-1 pb-1">
        <LanguageSelector />
        <ThemeToggle />
      </div>

      {user ? (
        <div className="flex items-center space-x-4 pb-1">
          <Link
            href="/profile"
            className="flex items-center space-x-2 text-gray-700 dark:text-gray-200 hover:text-primary-600 dark:hover:text-primary-400 transition-colors duration-150 group"
          >
            <UserAvatar
              user={user}
              size="sm"
              className="group-hover:shadow-md transition-shadow duration-150"
            />
            <span className="text-sm font-medium">{user.display_name || user.username}</span>
          </Link>
          <button
            onClick={logout}
            className="px-3 py-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:ring-offset-gray-900"
            suppressHydrationWarning
          >
            {t('nav.signOut')}
          </button>
        </div>
      ) : (
        <div className="flex items-center space-x-3 pb-1" suppressHydrationWarning>
          <Link href="/signin">
            <Button variant="ghost" size="sm" suppressHydrationWarning>
              {t('nav.signIn')}
            </Button>
          </Link>
          <Link href="/signup">
            <Button variant="primary" size="sm" suppressHydrationWarning>
              {t('nav.signUp')}
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}
