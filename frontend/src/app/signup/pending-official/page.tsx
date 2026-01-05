'use client';

import { useTranslation } from 'react-i18next';
import { Shield, Clock, CheckCircle } from 'lucide-react';
import Link from 'next/link';

export default function PendingOfficialPage() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <div className="max-w-md w-full text-center">
        <div className="mx-auto w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center mb-6">
          <Shield className="w-8 h-8 text-primary-600" />
        </div>

        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          {t('signup.officialRequestReceived')}
        </h1>

        <p className="text-gray-600 dark:text-gray-400 mb-6">
          {t('signup.officialRequestExplanation')}
        </p>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm mb-6">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
            {t('signup.whatHappensNext')}
          </h2>
          <ul className="space-y-3 text-left">
            <li className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {t('signup.step1AccountCreated')}
              </span>
            </li>
            <li className="flex items-start gap-3">
              <Clock className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {t('signup.step2ReviewPending')}
              </span>
            </li>
            <li className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-primary-500 mt-0.5 flex-shrink-0" />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {t('signup.step3AccessGranted')}
              </span>
            </li>
          </ul>
        </div>

        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          {t('signup.canUseNormally')}
        </p>

        <Link
          href="/"
          className="inline-flex items-center justify-center px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 transition-colors"
        >
          {t('signup.goToHome')}
        </Link>
      </div>
    </div>
  );
}
