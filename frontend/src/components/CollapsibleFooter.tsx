'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { ChevronUp, ChevronDown } from 'lucide-react';
import { useConfigTranslation } from '@/hooks/useConfigTranslation';
import Footer from './Footer';

export default function CollapsibleFooter() {
  const { t, instanceName } = useConfigTranslation();
  const [isExpanded, setIsExpanded] = useState(false);

  // Handle escape key to close expanded panel
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isExpanded) {
        setIsExpanded(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isExpanded]);

  // Prevent body scroll when expanded
  useEffect(() => {
    if (isExpanded) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isExpanded]);

  const toggleExpanded = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  const closePanel = useCallback(() => {
    setIsExpanded(false);
  }, []);

  return (
    <>
      {/* Backdrop when expanded */}
      {isExpanded && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40 transition-opacity duration-300"
          onClick={closePanel}
          aria-hidden="true"
        />
      )}

      {/* Expanded footer panel */}
      <div
        id="expanded-footer-panel"
        className={`
          fixed bottom-0 left-0 right-0 z-50
          transform transition-transform duration-300 ease-out
          ${isExpanded ? 'translate-y-0' : 'translate-y-full pointer-events-none'}
          max-h-[80vh] overflow-auto
          rounded-t-2xl shadow-2xl
        `}
        role="region"
        aria-label={t('footer.legal')}
        aria-hidden={!isExpanded}
      >
        <Footer />
        {/* Close button - far right of footer */}
        <button
          onClick={toggleExpanded}
          className="absolute bottom-4 right-2 sm:right-4 p-2 rounded-lg bg-primary-700/50 hover:bg-primary-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
          aria-label={t('footer.collapse')}
        >
          <ChevronDown className="w-5 h-5 text-white" />
        </button>
      </div>

      {/* Mini footer bar - hidden when expanded */}
      <footer
        className={`fixed bottom-0 left-0 right-0 z-50 h-12 bg-gradient-to-r from-primary-950 to-primary-800 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] border-t border-primary-700 transition-opacity duration-300 ${isExpanded ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
        role="contentinfo"
      >
        <div className="h-full px-4 sm:px-6 pr-16 sm:pr-20 flex items-center justify-between max-w-7xl mx-auto">
          {/* Left side: Logo and title */}
          <Link href="/" className="flex items-center gap-2 group shrink-0">
            <Image
              src="/static/images/logo_tr3.svg"
              alt={instanceName}
              width={24}
              height={24}
              className="h-6 w-6 brightness-0 invert"
            />
            <span
              className="hidden sm:inline text-sm font-medium text-white group-hover:text-primary-200 transition-colors whitespace-nowrap"
              suppressHydrationWarning
            >
              {instanceName}{' '}
              <span className="text-primary-300 font-normal">
                {t('footer.poweredBy')} <span className="text-primary-200">OpenCitiVibes</span>
              </span>
            </span>
          </Link>

          {/* Legal links */}
          <div className="flex items-center gap-2 sm:gap-4 text-xs">
            <div className="hidden sm:block h-4 w-px bg-primary-600" aria-hidden="true" />
            <Link
              href="/privacy"
              className="hidden sm:inline text-primary-200 hover:text-white transition-colors"
            >
              {t('footer.privacy')}
            </Link>
            <Link href="/terms" className="text-primary-200 hover:text-white transition-colors">
              <span className="sm:hidden">{t('footer.legal')}</span>
              <span className="hidden sm:inline">{t('footer.terms')}</span>
            </Link>
            <Link
              href="/contact"
              className="hidden sm:inline text-primary-200 hover:text-white transition-colors"
            >
              {t('footer.contact')}
            </Link>
          </div>
        </div>

        {/* Expand button - far right of footer */}
        <button
          onClick={toggleExpanded}
          className="absolute right-2 sm:right-4 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-primary-700/50 hover:bg-primary-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary-900"
          aria-expanded={isExpanded}
          aria-controls="expanded-footer-panel"
          aria-label={t('footer.expand')}
        >
          <ChevronUp className="w-5 h-5 text-white" />
        </button>
      </footer>

      {/* Spacer to prevent content from being hidden behind mini footer */}
      <div className="h-12" aria-hidden="true" />
    </>
  );
}
