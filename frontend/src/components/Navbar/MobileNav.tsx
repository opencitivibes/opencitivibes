'use client';

import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { BarChart3 } from 'lucide-react';
import { User } from '@/types';
import { Button } from '../Button';
import { ThemeToggle } from '../ThemeToggle';
import { AdminMenuItemsMobile } from './AdminMenuItems';
import { UserAvatar } from './UserAvatar';
import { LanguageSelector } from './LanguageSelector';

interface MobileNavProps {
  user: User | null;
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
  getMobileNavLinkClass: (href: string) => string;
  isActive: (href: string) => boolean;
  logout: () => void;
}

export function MobileMenuButton({
  mobileMenuOpen,
  setMobileMenuOpen,
}: {
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
}) {
  return (
    <div className="md:hidden flex items-center space-x-2">
      {/* Mobile Search Icon */}
      <Link
        href="/search"
        className="p-2 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:ring-offset-gray-900"
        aria-label="Search"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </Link>
      <LanguageSelector />
      <ThemeToggle />
      <button
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        className="p-2 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:ring-offset-gray-900"
        aria-label="Toggle menu"
        aria-expanded={mobileMenuOpen}
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {mobileMenuOpen ? (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          ) : (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          )}
        </svg>
      </button>
    </div>
  );
}

export function MobileNav({
  user,
  mobileMenuOpen,
  setMobileMenuOpen,
  getMobileNavLinkClass,
  isActive,
  logout,
}: MobileNavProps) {
  const { t } = useTranslation();

  const closeMobileMenu = () => setMobileMenuOpen(false);

  if (!mobileMenuOpen) return null;

  return (
    <div
      className="md:hidden py-4 space-y-1 border-t border-gray-200 dark:border-gray-700 animate-fade-in"
      suppressHydrationWarning
    >
      <Link
        href="/"
        className={getMobileNavLinkClass('/')}
        onClick={closeMobileMenu}
        suppressHydrationWarning
      >
        {t('nav.home')}
      </Link>

      {user && (
        <>
          {/* Hide My Ideas and Submit for officials (non-admin) */}
          {(!user.is_official || user.is_global_admin) && (
            <>
              <Link
                href="/my-ideas"
                className={getMobileNavLinkClass('/my-ideas')}
                onClick={closeMobileMenu}
              >
                {t('nav.myIdeas')}
              </Link>
              <Link
                href="/submit"
                className={getMobileNavLinkClass('/submit')}
                onClick={closeMobileMenu}
              >
                {t('nav.submitIdea')}
              </Link>
            </>
          )}
          {user.is_official && !user.is_global_admin && (
            <Link
              href="/officials"
              className={`${getMobileNavLinkClass('/officials')} flex items-center gap-2`}
              onClick={closeMobileMenu}
            >
              <BarChart3 className="w-4 h-4" />
              {t('nav.officialDashboard')}
            </Link>
          )}
          {user.is_global_admin && (
            <AdminMenuItemsMobile
              getMobileNavLinkClass={getMobileNavLinkClass}
              onItemClick={closeMobileMenu}
            />
          )}
        </>
      )}

      {user ? (
        <div className="pt-3 border-t border-gray-200 dark:border-gray-700 space-y-3">
          <Link
            href="/profile"
            className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors duration-150 group focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:ring-offset-gray-900 ${
              isActive('/profile')
                ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                : 'text-gray-700 dark:text-gray-200 hover:bg-primary-50 dark:hover:bg-primary-900/30'
            }`}
            onClick={closeMobileMenu}
          >
            <UserAvatar
              user={user}
              size="md"
              className="group-hover:shadow-md transition-shadow duration-150"
            />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-200 group-hover:text-primary-600 dark:group-hover:text-primary-400">
              {user.display_name || user.username}
            </span>
          </Link>
          <div className="px-3">
            <button
              onClick={() => {
                logout();
                closeMobileMenu();
              }}
              className="w-full px-3 py-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors text-sm font-medium text-center focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:ring-offset-gray-900"
            >
              {t('nav.signOut')}
            </button>
          </div>
        </div>
      ) : (
        <div className="pt-3 border-t border-gray-200 dark:border-gray-700 space-y-2 px-3">
          <Link href="/signin" className="block" onClick={closeMobileMenu}>
            <Button variant="ghost" size="sm" className="w-full">
              {t('nav.signIn')}
            </Button>
          </Link>
          <Link href="/signup" className="block" onClick={closeMobileMenu}>
            <Button variant="primary" size="sm" className="w-full">
              {t('nav.signUp')}
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}
