'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/Button';
import { usePlatformConfig } from '@/lib/config/PlatformConfigProvider';
import { contactAPI, type ContactSubject } from '@/lib/api';

export default function ContactPageClient() {
  const { t, i18n } = useTranslation();
  const { config } = usePlatformConfig();
  const contactEmail = config?.contact.email || 'contact@opencitivibes.local';
  const [formState, setFormState] = useState({
    name: '',
    email: '',
    subject: '' as ContactSubject | '',
    message: '',
  });
  const [submitted, setSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const language = i18n.language?.startsWith('fr') ? 'fr' : 'en';
      await contactAPI.submit({
        name: formState.name,
        email: formState.email,
        subject: formState.subject as ContactSubject,
        message: formState.message,
        language,
      });
      setSubmitted(true);
      setFormState({ name: '', email: '', subject: '', message: '' });
    } catch (err) {
      // Handle specific error cases using type casting (avoids direct axios import)
      const axiosError = err as import('axios').AxiosError<{ detail?: string }>;
      if (axiosError.response) {
        const status = axiosError.response.status;
        if (status === 429) {
          // Rate limited
          setError(t('contactPage.errorRateLimited'));
        } else if (axiosError.response.data?.detail) {
          // Server provided error message
          setError(axiosError.response.data.detail);
        } else {
          setError(t('contactPage.errorSending'));
        }
      } else {
        setError(t('contactPage.errorSending'));
      }
      console.error('Contact form submission failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    setFormState((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-md p-8 md:p-12">
          <Link
            href="/"
            className="inline-flex items-center text-primary-600 hover:text-primary-700 mb-6 transition-colors"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            {t('common.backToHome')}
          </Link>

          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">
            {t('contactPage.title')}
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300 mb-8">
            {t('contactPage.subtitle')}
          </p>

          {submitted ? (
            <div className="bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-xl p-6 text-center">
              <svg
                className="w-12 h-12 text-success-500 mx-auto mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <h2 className="text-xl font-semibold text-success-800 dark:text-success-200 mb-2">
                {t('contactPage.messageSent')}
              </h2>
              <p className="text-success-700 dark:text-success-300">{t('contactPage.thankYou')}</p>
              <Button variant="primary" className="mt-6" onClick={() => setSubmitted(false)}>
                {t('contactPage.sendAnother')}
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label
                    htmlFor="name"
                    className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                  >
                    {t('contactPage.name')} *
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    required
                    value={formState.name}
                    onChange={handleChange}
                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
                    placeholder={t('contactPage.namePlaceholder')}
                  />
                </div>
                <div>
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                  >
                    {t('contactPage.email')} *
                  </label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    required
                    value={formState.email}
                    onChange={handleChange}
                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
                    placeholder={t('contactPage.emailPlaceholder')}
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="subject"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  {t('contactPage.subject')} *
                </label>
                <select
                  id="subject"
                  name="subject"
                  required
                  value={formState.subject}
                  onChange={handleChange}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  <option value="">{t('contactPage.subjectPlaceholder')}</option>
                  <option value="general">{t('contactPage.subjectGeneral')}</option>
                  <option value="account">{t('contactPage.subjectAccount')}</option>
                  <option value="idea">{t('contactPage.subjectIdea')}</option>
                  <option value="bug">{t('contactPage.subjectBug')}</option>
                  <option value="feedback">{t('contactPage.subjectFeedback')}</option>
                  <option value="privacy">{t('contactPage.subjectPrivacy')}</option>
                  <option value="other">{t('contactPage.subjectOther')}</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="message"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  {t('contactPage.message')} *
                </label>
                <textarea
                  id="message"
                  name="message"
                  required
                  rows={6}
                  value={formState.message}
                  onChange={handleChange}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors resize-none bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
                  placeholder={t('contactPage.messagePlaceholder')}
                />
              </div>

              {error && (
                <div className="bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-lg p-4">
                  <p className="text-danger-700 dark:text-danger-300 text-sm">{error}</p>
                </div>
              )}

              <div className="flex items-center justify-between pt-4">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  * {t('contactPage.requiredFields')}
                </p>
                <Button type="submit" variant="primary" size="lg" disabled={isSubmitting}>
                  {isSubmitting ? t('contactPage.sending') : t('contactPage.sendMessage')}
                </Button>
              </div>
            </form>
          )}

          {/* Additional Contact Info */}
          <div className="mt-12 pt-8 border-t border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
              {t('contactPage.otherWays')}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
                  <svg
                    className="w-5 h-5 text-primary-600 dark:text-primary-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    />
                  </svg>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900 dark:text-gray-100">
                    {t('contactPage.email')}
                  </h3>
                  <a
                    href={`mailto:${contactEmail}`}
                    className="text-primary-600 dark:text-primary-400 hover:underline text-sm"
                  >
                    {contactEmail}
                  </a>
                </div>
              </div>
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
                  <svg
                    className="w-5 h-5 text-primary-600 dark:text-primary-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900 dark:text-gray-100">
                    {t('contactPage.responseTime')}
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400 text-sm">
                    {t('contactPage.responseTimeValue')}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
