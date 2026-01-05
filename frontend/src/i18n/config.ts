import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// Dynamic import for translations - only loads the needed language
const loadTranslations = async (language: string) => {
  switch (language) {
    case 'en':
      return (await import('./locales/en.json')).default;
    case 'es':
      return (await import('./locales/es.json')).default;
    case 'fr':
    default:
      return (await import('./locales/fr.json')).default;
  }
};

// Get initial language from localStorage or default to 'fr'
const getInitialLanguage = (): string => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('i18nextLng') || 'fr';
  }
  return 'fr';
};

// Initialize with empty resources - will be loaded dynamically
i18n.use(initReactI18next).init({
  resources: {},
  lng: getInitialLanguage(),
  fallbackLng: 'fr',
  interpolation: {
    escapeValue: false,
  },
  react: {
    useSuspense: false, // Disable suspense for SSR compatibility
  },
});

// Load initial translations
const initLanguage = getInitialLanguage();
loadTranslations(initLanguage).then((translations) => {
  i18n.addResourceBundle(initLanguage, 'translation', translations, true, true);
});

// Override changeLanguage to dynamically load translations
const originalChangeLanguage = i18n.changeLanguage.bind(i18n);
i18n.changeLanguage = async (lng: string) => {
  // Check if language is already loaded
  if (!i18n.hasResourceBundle(lng, 'translation')) {
    const translations = await loadTranslations(lng);
    i18n.addResourceBundle(lng, 'translation', translations, true, true);
  }
  return originalChangeLanguage(lng);
};

export default i18n;
