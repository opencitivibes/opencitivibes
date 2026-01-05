'use client';

import { useState, useMemo } from 'react';
import { usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { SearchBar } from '../search/SearchBar';
import { DesktopNav } from './DesktopNav';
import { MobileNav, MobileMenuButton } from './MobileNav';
import { createNavLinkClass, createMobileNavLinkClass, createIsActive } from './utils';
import { Logo } from '../Logo';

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [adminMenuOpen, setAdminMenuOpen] = useState(false);

  // Memoize class generators to avoid recreating on each render
  const getNavLinkClass = useMemo(() => createNavLinkClass(pathname), [pathname]);
  const getMobileNavLinkClass = useMemo(() => createMobileNavLinkClass(pathname), [pathname]);
  const isActive = useMemo(() => createIsActive(pathname), [pathname]);

  return (
    <nav className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo / Brand */}
          <Logo size="md" />

          {/* Desktop Search Bar */}
          <div className="hidden md:block flex-1 max-w-md mx-4">
            <SearchBar compact showAutocomplete />
          </div>

          {/* Desktop Navigation */}
          <DesktopNav
            user={user}
            getNavLinkClass={getNavLinkClass}
            logout={logout}
            adminMenuOpen={adminMenuOpen}
            setAdminMenuOpen={setAdminMenuOpen}
          />

          {/* Mobile Menu Button */}
          <MobileMenuButton mobileMenuOpen={mobileMenuOpen} setMobileMenuOpen={setMobileMenuOpen} />
        </div>

        {/* Mobile Navigation */}
        <MobileNav
          user={user}
          mobileMenuOpen={mobileMenuOpen}
          setMobileMenuOpen={setMobileMenuOpen}
          getMobileNavLinkClass={getMobileNavLinkClass}
          isActive={isActive}
          logout={logout}
        />
      </div>
    </nav>
  );
}
