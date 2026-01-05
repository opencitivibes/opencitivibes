'use client';

import { useState, useEffect } from 'react';
import { ChevronUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export function ScrollToTop() {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const toggleVisibility = () => {
      setVisible(window.scrollY > 500);
    };

    window.addEventListener('scroll', toggleVisibility);
    return () => window.removeEventListener('scroll', toggleVisibility);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (!visible) return null;

  return (
    <button
      onClick={scrollToTop}
      className="fixed bottom-16 right-6 p-3 bg-primary-500 text-white rounded-full
                 shadow-lg hover:bg-primary-600 transition-all duration-200
                 hover:shadow-xl focus:outline-none focus:ring-2
                 focus:ring-primary-500 focus:ring-offset-2
                 animate-fade-in z-50"
      aria-label={t('common.scrollToTop')}
    >
      <ChevronUp className="w-6 h-6" aria-hidden="true" />
    </button>
  );
}

export default ScrollToTop;
