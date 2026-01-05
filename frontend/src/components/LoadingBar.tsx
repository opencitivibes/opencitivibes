'use client';

import { useEffect, useState, useRef } from 'react';
import { usePathname } from 'next/navigation';

export function LoadingBar() {
  const [loading, setLoading] = useState(false);
  const pathname = usePathname();
  const previousPathname = useRef(pathname);
  const loadingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Only trigger loading when pathname actually changes
    if (previousPathname.current !== pathname) {
      previousPathname.current = pathname;

      // Clear any existing timers
      if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current);
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);

      // Use setTimeout to avoid synchronous setState in effect
      loadingTimerRef.current = setTimeout(() => {
        setLoading(true);
      }, 0);

      hideTimerRef.current = setTimeout(() => {
        setLoading(false);
      }, 500);
    }

    return () => {
      if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current);
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    };
  }, [pathname]);

  if (!loading) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 h-1 bg-gray-200">
      <div className="h-full bg-gradient-to-r from-primary-500 to-pink-500 animate-loading-bar" />
    </div>
  );
}

export default LoadingBar;
