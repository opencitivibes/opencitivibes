'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { AlertTriangle, MessageSquare, ThumbsUp } from 'lucide-react';
import type { Idea } from '@/types';

interface EditApprovedIdeaDialogProps {
  idea: Idea;
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function EditApprovedIdeaDialog({
  idea,
  isOpen,
  onConfirm,
  onCancel,
}: EditApprovedIdeaDialogProps) {
  const { t } = useTranslation();
  const [confirmed, setConfirmed] = useState(false);

  const handleConfirm = (e: React.MouseEvent) => {
    e.preventDefault();
    if (confirmed) {
      onConfirm();
      setConfirmed(false);
    }
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setConfirmed(false);
      onCancel();
    }
  };

  // Calculate remaining edits (max 3 per month)
  const remainingEdits = Math.max(0, 3 - (idea.edit_count || 0));

  return (
    <AlertDialog open={isOpen} onOpenChange={handleOpenChange}>
      <AlertDialogContent className="bg-white dark:bg-gray-800 max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning-500" />
            {t('ideas.editApprovedTitle', 'Edit Approved Idea')}
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-4">
              {/* Warning message */}
              <p className="text-warning-600 dark:text-warning-400 font-medium">
                {t(
                  'ideas.editApprovedWarning',
                  'Editing this idea will send it back for moderation'
                )}
              </p>

              {/* Consequences explanation */}
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 space-y-2 text-sm">
                <p className="text-gray-700 dark:text-gray-300">
                  {t('ideas.ideaHiddenDuringReview', 'Your idea will be hidden until re-approved')}
                </p>

                {/* Preserved data */}
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                  <ThumbsUp className="h-4 w-4 text-success-500" />
                  <span>
                    {t('ideas.votesPreserved', 'Your {{count}} votes will be preserved', {
                      count: idea.upvotes + idea.downvotes,
                    })}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                  <MessageSquare className="h-4 w-4 text-primary-500" />
                  <span>
                    {t('ideas.commentsPreserved', 'Your {{count}} comments will be preserved', {
                      count: idea.comment_count,
                    })}
                  </span>
                </div>
              </div>

              {/* Remaining edits */}
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {t('ideas.editRemainingThisMonth', 'Edits remaining this month: {{count}}', {
                  count: remainingEdits,
                })}
              </p>

              {/* Confirmation checkbox */}
              <div className="flex items-start gap-2 pt-2">
                <Checkbox
                  id="confirm-edit"
                  checked={confirmed}
                  onCheckedChange={(checked) => setConfirmed(!!checked)}
                  className="mt-1"
                />
                <Label
                  htmlFor="confirm-edit"
                  className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer leading-relaxed"
                >
                  {t(
                    'ideas.editApprovedConfirmCheckbox',
                    'I understand my idea will be hidden until re-approved by moderators'
                  )}
                </Label>
              </div>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>

        <AlertDialogFooter>
          <AlertDialogCancel onClick={onCancel}>{t('common.cancel', 'Cancel')}</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={!confirmed}
            className="bg-warning-600 hover:bg-warning-700 text-white focus:ring-warning-600"
          >
            {t('ideas.editApprovedConfirm', 'Confirm Edit')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
