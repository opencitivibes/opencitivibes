'use client';

import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/Alert';

interface HiddenContentPlaceholderProps {
  contentType: 'comment' | 'idea';
}

export function HiddenContentPlaceholder({ contentType }: HiddenContentPlaceholderProps) {
  const { t } = useTranslation();

  return (
    <Alert variant="info" className="bg-gray-50 border-dashed border-gray-300">
      <div className="flex items-center gap-2">
        <svg
          className="h-4 w-4 text-gray-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
          />
        </svg>
        <div>
          <p className="text-sm font-medium text-gray-700">
            {t('moderation.contentHidden', {
              type: contentType === 'comment' ? t('moderation.comment') : t('moderation.idea'),
            })}
          </p>
          <p className="text-xs text-gray-500">{t('moderation.hiddenExplanation')}</p>
        </div>
      </div>
    </Alert>
  );
}
