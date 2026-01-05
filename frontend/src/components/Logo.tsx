'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePlatformConfig } from '@/lib/config/PlatformConfigProvider';
import { useTheme } from '@/hooks/useTheme';

interface LogoProps {
  className?: string;
  showText?: boolean;
  size?: 'sm' | 'md' | 'lg';
  asLink?: boolean;
}

const SIZES = {
  sm: { width: 32, height: 32, className: 'h-8 w-auto' },
  md: { width: 40, height: 40, className: 'h-10 sm:h-12 w-auto' },
  lg: { width: 48, height: 48, className: 'h-12 sm:h-14 w-auto' },
};

/**
 * Dynamic logo component that uses platform configuration.
 * Falls back to default logo if no custom logo is configured.
 * Supports dark mode with an optional logo_dark variant.
 */
export function Logo({ className = '', showText = false, size = 'md', asLink = true }: LogoProps) {
  const { config, instanceName } = usePlatformConfig();
  const { isDark } = useTheme();

  const defaultLogo = process.env.NEXT_PUBLIC_DEFAULT_LOGO || '/static/images/logo_tr3.svg';

  // Use dark logo if available and in dark mode, otherwise regular logo
  const logoSrc =
    isDark && config?.branding?.logo_dark
      ? config.branding.logo_dark
      : config?.branding?.logo || defaultLogo;

  const dimensions = SIZES[size];

  const logoContent = (
    <>
      <Image
        src={logoSrc}
        alt={instanceName}
        width={dimensions.width}
        height={dimensions.height}
        className={`${dimensions.className} object-contain transition-transform duration-200 group-hover:scale-105`}
        priority
      />
      {showText && (
        <span className="font-semibold text-gray-900 dark:text-white">{instanceName}</span>
      )}
    </>
  );

  if (asLink) {
    return (
      <Link href="/" className={`flex items-center space-x-2 group ${className}`}>
        {logoContent}
      </Link>
    );
  }

  return <div className={`flex items-center space-x-2 ${className}`}>{logoContent}</div>;
}
