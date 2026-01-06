'use client';

import { useTranslation } from 'react-i18next';
import { Twitter, Facebook, Linkedin, MessageCircle, Link2, Check } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import { shareAPI } from '@/lib/api';
import {
  buildTwitterShareUrl,
  buildFacebookShareUrl,
  buildLinkedInShareUrl,
  buildWhatsAppShareUrl,
  copyToClipboard,
  getShareableUrl,
  openSharePopup,
} from '@/lib/share-utils';
import type { SharePlatform } from '@/types';

interface ShareButtonsProps {
  ideaId: number;
  ideaTitle: string;
  variant?: 'full' | 'compact';
  className?: string;
}

interface ShareButtonConfig {
  platform: SharePlatform;
  icon: React.ReactNode;
  labelKey: string;
  getUrl: (url: string, title: string) => string;
  color: string;
  hoverColor: string;
}

const shareButtons: ShareButtonConfig[] = [
  {
    platform: 'twitter',
    icon: <Twitter className="w-4 h-4" />,
    labelKey: 'share.twitter',
    getUrl: buildTwitterShareUrl,
    color: 'text-[#1DA1F2]',
    hoverColor: 'hover:bg-[#1DA1F2]/10',
  },
  {
    platform: 'facebook',
    icon: <Facebook className="w-4 h-4" />,
    labelKey: 'share.facebook',
    getUrl: (url) => buildFacebookShareUrl(url),
    color: 'text-[#1877F2]',
    hoverColor: 'hover:bg-[#1877F2]/10',
  },
  {
    platform: 'linkedin',
    icon: <Linkedin className="w-4 h-4" />,
    labelKey: 'share.linkedin',
    getUrl: (url) => buildLinkedInShareUrl(url),
    color: 'text-[#0A66C2]',
    hoverColor: 'hover:bg-[#0A66C2]/10',
  },
  {
    platform: 'whatsapp',
    icon: <MessageCircle className="w-4 h-4" />,
    labelKey: 'share.whatsapp',
    getUrl: buildWhatsAppShareUrl,
    color: 'text-[#25D366]',
    hoverColor: 'hover:bg-[#25D366]/10',
  },
];

export function ShareButtons({
  ideaId,
  ideaTitle,
  variant = 'full',
  className = '',
}: ShareButtonsProps) {
  const { t } = useTranslation();
  const [copiedRecently, setCopiedRecently] = useState(false);

  const handleShare = async (
    platform: SharePlatform,
    getUrl: (url: string, title: string) => string
  ) => {
    const currentUrl = typeof window !== 'undefined' ? window.location.href : '';
    const shareUrl = getUrl(currentUrl, ideaTitle);

    // Open share popup
    openSharePopup(shareUrl, `share-${platform}`);

    // Record share event (fire-and-forget)
    shareAPI.recordShare(ideaId, platform).catch(() => {
      // Silent fail - don't interrupt user experience
    });
  };

  const handleCopyLink = async () => {
    try {
      const shareUrl = getShareableUrl();
      await copyToClipboard(shareUrl);
      setCopiedRecently(true);
      toast.success(t('share.linkCopied'));

      // Reset the copied state after 2 seconds
      setTimeout(() => setCopiedRecently(false), 2000);

      // Record share event (fire-and-forget)
      shareAPI.recordShare(ideaId, 'copy_link').catch(() => {
        // Silent fail
      });
    } catch {
      toast.error(t('common.error'));
    }
  };

  if (variant === 'compact') {
    return (
      <div className={`flex items-center gap-1 ${className}`}>
        {shareButtons.map((btn) => (
          <button
            key={btn.platform}
            onClick={() => handleShare(btn.platform, btn.getUrl)}
            className={`p-2 rounded-full transition-colors ${btn.color} ${btn.hoverColor}`}
            aria-label={t(btn.labelKey)}
            title={t(btn.labelKey)}
          >
            {btn.icon}
          </button>
        ))}
        <button
          onClick={handleCopyLink}
          className={`p-2 rounded-full transition-colors text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800`}
          aria-label={t('share.copyLink')}
          title={t('share.copyLink')}
        >
          {copiedRecently ? (
            <Check className="w-4 h-4 text-green-500" />
          ) : (
            <Link2 className="w-4 h-4" />
          )}
        </button>
      </div>
    );
  }

  return (
    <div className={`${className}`}>
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
        {t('share.title')}
      </h3>
      <div className="flex flex-wrap items-center gap-2">
        {shareButtons.map((btn) => (
          <button
            key={btn.platform}
            onClick={() => handleShare(btn.platform, btn.getUrl)}
            className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700
              bg-white dark:bg-gray-800 transition-all duration-150
              hover:border-gray-300 dark:hover:border-gray-600 ${btn.hoverColor}
              focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900`}
            aria-label={t(btn.labelKey)}
          >
            <span className={btn.color}>{btn.icon}</span>
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {t(btn.labelKey).replace('Share on ', '').replace('Partager sur ', '')}
            </span>
          </button>
        ))}
        <button
          onClick={handleCopyLink}
          className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700
            bg-white dark:bg-gray-800 transition-all duration-150
            hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700
            focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900`}
          aria-label={t('share.copyLink')}
        >
          {copiedRecently ? (
            <>
              <Check className="w-4 h-4 text-green-500" />
              <span className="text-sm text-green-600 dark:text-green-400">
                {t('share.linkCopied').replace('!', '')}
              </span>
            </>
          ) : (
            <>
              <Link2 className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {t('share.copyLink')}
              </span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
