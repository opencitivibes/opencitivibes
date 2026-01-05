/**
 * Construct avatar URLs using relative paths (proxied through Next.js rewrites).
 * This avoids SSR hydration mismatch when accessing from different hosts.
 *
 * Backend stores paths like: data/uploads/avatars/xxx.png
 * We convert to: /uploads/avatars/xxx.png (proxied to backend via next.config.js rewrites)
 */
export const getAvatarUrl = (avatarPath: string): string => {
  // Remove 'data/' prefix if present and ensure leading slash
  const cleanPath = avatarPath.replace(/^data\//, '').replace(/^\/+/, '');
  return `/${cleanPath}`;
};

/**
 * Generate nav link classes based on active state (desktop)
 */
export const createNavLinkClass =
  (pathname: string) =>
  (href: string): string => {
    const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);
    const base =
      'font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900 pb-1 border-b-2';
    return isActive
      ? `${base} text-primary-600 dark:text-primary-400 border-primary-500`
      : `${base} text-gray-700 dark:text-gray-200 hover:text-primary-600 dark:hover:text-primary-400 border-transparent`;
  };

/**
 * Generate mobile nav link classes with active state
 */
export const createMobileNavLinkClass =
  (pathname: string) =>
  (href: string): string => {
    const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);
    const base =
      'block py-2.5 px-3 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:ring-offset-gray-900';
    return isActive
      ? `${base} bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400`
      : `${base} text-gray-700 dark:text-gray-200 hover:bg-primary-50 dark:hover:bg-primary-900/30 hover:text-primary-600 dark:hover:text-primary-400`;
  };

/**
 * Check if a path is active
 */
export const createIsActive =
  (pathname: string) =>
  (href: string): boolean => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };
