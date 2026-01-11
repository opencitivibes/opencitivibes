'use client';

import { useTheme } from 'next-themes';
import { Toaster as Sonner } from 'sonner';
import { CheckCircle, XCircle, AlertTriangle, Info, Loader2 } from 'lucide-react';

type ToasterProps = React.ComponentProps<typeof Sonner>;

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = 'system' } = useTheme();

  return (
    <Sonner
      theme={theme as ToasterProps['theme']}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            'group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-xl group-[.toaster]:rounded-xl',
          description: 'group-[.toast]:text-muted-foreground',
          actionButton:
            'group-[.toast]:bg-primary group-[.toast]:text-primary-foreground group-[.toast]:font-medium',
          cancelButton: 'group-[.toast]:bg-muted group-[.toast]:text-muted-foreground',
          success:
            'group-[.toaster]:bg-success-50 group-[.toaster]:text-success-900 group-[.toaster]:border-success-200 dark:group-[.toaster]:bg-success-950 dark:group-[.toaster]:text-success-100 dark:group-[.toaster]:border-success-800',
          error:
            'group-[.toaster]:bg-error-50 group-[.toaster]:text-error-900 group-[.toaster]:border-error-200 dark:group-[.toaster]:bg-error-950 dark:group-[.toaster]:text-error-100 dark:group-[.toaster]:border-error-800',
          warning:
            'group-[.toaster]:bg-warning-50 group-[.toaster]:text-warning-900 group-[.toaster]:border-warning-200 dark:group-[.toaster]:bg-warning-950 dark:group-[.toaster]:text-warning-100 dark:group-[.toaster]:border-warning-800',
          info: 'group-[.toaster]:bg-info-50 group-[.toaster]:text-info-900 group-[.toaster]:border-info-200 dark:group-[.toaster]:bg-info-950 dark:group-[.toaster]:text-info-100 dark:group-[.toaster]:border-info-800',
        },
        style: {
          padding: '16px 20px',
          fontSize: '14px',
          borderRadius: '12px',
          minWidth: '320px',
          maxWidth: '420px',
        },
      }}
      icons={{
        success: <CheckCircle className="h-5 w-5 text-success-500" />,
        error: <XCircle className="h-5 w-5 text-error-500" />,
        warning: <AlertTriangle className="h-5 w-5 text-warning-500" />,
        info: <Info className="h-5 w-5 text-info-500" />,
        loading: <Loader2 className="h-5 w-5 text-primary-500 animate-spin" />,
      }}
      {...props}
    />
  );
};

export { Toaster };
