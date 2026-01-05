'use client';

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/Button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { moderationAPI } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { FlagDialog } from './FlagDialog';
import type { ContentType, FlagReason } from '@/types/moderation';

interface FlagButtonProps {
  contentType: ContentType;
  contentId: number;
  contentAuthorId: number;
  contentPreview: string;
  onFlagged?: () => void;
  variant?: 'icon' | 'text';
  size?: 'sm' | 'md';
}

export function FlagButton({
  contentType,
  contentId,
  contentAuthorId,
  contentPreview,
  onFlagged,
  variant = 'icon',
  size = 'sm',
}: FlagButtonProps) {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const isAuthenticated = !!user;
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isFlagged, setIsFlagged] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  // Check if user already flagged this content
  useEffect(() => {
    const checkFlagStatus = async () => {
      if (!isAuthenticated) {
        setIsChecking(false);
        return;
      }

      try {
        const result = await moderationAPI.checkFlagStatus(contentType, contentId);
        setIsFlagged(result.flagged);
      } catch (error) {
        console.error('Failed to check flag status:', error);
      } finally {
        setIsChecking(false);
      }
    };

    checkFlagStatus();
  }, [contentType, contentId, isAuthenticated]);

  // Don't show flag button for own content
  if (user?.id === contentAuthorId) {
    return null;
  }

  // Don't show if not authenticated
  if (!isAuthenticated) {
    return null;
  }

  const handleFlag = async (reason: FlagReason, details?: string) => {
    setIsLoading(true);
    try {
      await moderationAPI.createFlag({
        content_type: contentType,
        content_id: contentId,
        reason,
        details,
      });
      setIsFlagged(true);
      setIsDialogOpen(false);
      onFlagged?.();
    } catch (error) {
      console.error('Failed to flag content:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  if (isChecking) {
    return (
      <Button variant="ghost" size={size} disabled className="opacity-50">
        <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      </Button>
    );
  }

  if (isFlagged) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size={size} disabled className="text-gray-400">
              <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              {variant === 'text' && t('moderation.flagged')}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>{t('moderation.alreadyFlagged')}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size={size}
              onClick={(e) => {
                e.stopPropagation();
                setIsDialogOpen(true);
              }}
              className="text-gray-500 hover:text-error-600"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"
                />
              </svg>
              {variant === 'text' && <span className="ml-1">{t('moderation.flag')}</span>}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>{t('moderation.reportContent')}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <FlagDialog
        contentType={contentType}
        contentPreview={contentPreview}
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onSubmit={handleFlag}
        isLoading={isLoading}
      />
    </>
  );
}
