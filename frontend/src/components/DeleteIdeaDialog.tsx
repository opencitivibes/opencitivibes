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
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/Button';
import { Textarea } from '@/components/Textarea';
import { Trash2 } from 'lucide-react';

interface DeleteIdeaDialogProps {
  ideaTitle: string;
  isAdmin?: boolean;
  onDelete: (reason?: string) => Promise<void>;
  onSuccess?: () => void;
  trigger?: React.ReactNode;
}

export function DeleteIdeaDialog({
  ideaTitle,
  isAdmin = false,
  onDelete,
  onSuccess,
  trigger,
}: DeleteIdeaDialogProps) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async (e: React.MouseEvent) => {
    // Prevent default AlertDialogAction behavior
    e.preventDefault();

    // Admin requires reason
    if (isAdmin && !reason.trim()) {
      setError(t('ideaDeletion.reasonRequired'));
      return;
    }

    setIsDeleting(true);
    setError(null);

    try {
      await onDelete(reason.trim() || undefined);
      setIsOpen(false);
      setReason('');
      onSuccess?.();
    } catch (err) {
      console.error('Failed to delete idea:', err);
      setError(t('toast.error'));
    } finally {
      setIsDeleting(false);
    }
  };

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    if (!open) {
      setReason('');
      setError(null);
    }
  };

  return (
    <AlertDialog open={isOpen} onOpenChange={handleOpenChange}>
      <AlertDialogTrigger asChild>
        {trigger || (
          <Button
            variant="secondary"
            size="sm"
            className="border-error-500 text-error-600 hover:bg-error-50"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            {t('ideaDeletion.deleteIdea')}
          </Button>
        )}
      </AlertDialogTrigger>
      <AlertDialogContent className="bg-white dark:bg-gray-800">
        <AlertDialogHeader>
          <AlertDialogTitle>
            {isAdmin ? t('ideaDeletion.adminDeleteTitle') : t('ideaDeletion.deleteConfirmTitle')}
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div>
              <span className="font-medium text-gray-900 dark:text-gray-100">
                &quot;{ideaTitle}&quot;
              </span>
              <br />
              <br />
              <span>
                {isAdmin
                  ? t('ideaDeletion.adminDeleteMessage')
                  : t('ideaDeletion.deleteConfirmMessage')}
              </span>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="py-2">
          <label
            htmlFor="delete-reason"
            className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2"
          >
            {isAdmin ? t('ideaDeletion.adminDeleteReason') : t('ideaDeletion.deleteReason')}
          </label>
          <Textarea
            id="delete-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={t('ideaDeletion.deleteReasonPlaceholder')}
            rows={3}
            maxLength={500}
            error={!!error}
          />
          {error && <p className="text-sm text-error-500 mt-2">{error}</p>}
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>
            {t('ideaDeletion.cancelButton')}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleDelete}
            disabled={isDeleting || (isAdmin && !reason.trim())}
            className="bg-error-600 hover:bg-error-700 text-white focus:ring-error-600"
          >
            {isDeleting ? t('toast.deleting') : t('ideaDeletion.deleteButton')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
