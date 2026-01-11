'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
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

type DialogVariant = 'danger' | 'warning' | 'default';

interface ConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: DialogVariant;
  onConfirm: () => Promise<void>;
  isLoading?: boolean;
}

const variantStyles: Record<
  DialogVariant,
  { icon: typeof AlertTriangle; titleClass: string; buttonClass: string }
> = {
  danger: {
    icon: AlertTriangle,
    titleClass: 'text-error-600 dark:text-error-400',
    buttonClass: 'bg-error-500 hover:bg-error-600 focus:ring-error-500',
  },
  warning: {
    icon: AlertCircle,
    titleClass: 'text-warning-600 dark:text-warning-400',
    buttonClass: 'bg-warning-500 hover:bg-warning-600 focus:ring-warning-500',
  },
  default: {
    icon: Info,
    titleClass: 'text-gray-900 dark:text-gray-100',
    buttonClass: 'bg-primary-500 hover:bg-primary-600 focus:ring-primary-500',
  },
};

export function ConfirmationDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel,
  variant = 'default',
  onConfirm,
  isLoading = false,
}: ConfirmationDialogProps) {
  const { t } = useTranslation();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { icon: Icon, titleClass, buttonClass } = variantStyles[variant];

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch {
      // Error handling is done in the parent component
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!isSubmitting) {
      onOpenChange(newOpen);
    }
  };

  const processing = isLoading || isSubmitting;

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className={`flex items-center gap-2 ${titleClass}`}>
            <Icon className="h-5 w-5" aria-hidden="true" />
            {title}
          </AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={processing}>
            {cancelLabel || t('common.cancel')}
          </AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirm} disabled={processing} className={buttonClass}>
            {processing ? t('common.processing') : confirmLabel || t('confirmDialog.confirm')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
