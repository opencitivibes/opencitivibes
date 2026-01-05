import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';

/**
 * Custom hook for showing toasts with i18n support.
 *
 * @example
 * ```tsx
 * const { success, error } = useToast();
 *
 * // Using translation key
 * success('toast.profileUpdated');
 *
 * // With interpolation
 * success('toast.welcomeBack', { name: user.name });
 *
 * // Direct message (for dynamic content)
 * error(apiError.message, { isRaw: true });
 * ```
 */
export function useToast() {
  const { t } = useTranslation();

  const success = useCallback(
    (keyOrMessage: string, paramsOrOptions?: Record<string, unknown> | { isRaw?: boolean }) => {
      const isRaw = (paramsOrOptions as { isRaw?: boolean })?.isRaw;
      const message = isRaw ? keyOrMessage : t(keyOrMessage, paramsOrOptions);
      return toast.success(message, { duration: 4000 });
    },
    [t]
  );

  const error = useCallback(
    (keyOrMessage: string, paramsOrOptions?: Record<string, unknown> | { isRaw?: boolean }) => {
      const isRaw = (paramsOrOptions as { isRaw?: boolean })?.isRaw;
      const message = isRaw ? keyOrMessage : t(keyOrMessage, paramsOrOptions);
      return toast.error(message, { duration: 6000 });
    },
    [t]
  );

  const warning = useCallback(
    (keyOrMessage: string, paramsOrOptions?: Record<string, unknown> | { isRaw?: boolean }) => {
      const isRaw = (paramsOrOptions as { isRaw?: boolean })?.isRaw;
      const message = isRaw ? keyOrMessage : t(keyOrMessage, paramsOrOptions);
      return toast.warning(message, { duration: 5000 });
    },
    [t]
  );

  const info = useCallback(
    (keyOrMessage: string, paramsOrOptions?: Record<string, unknown> | { isRaw?: boolean }) => {
      const isRaw = (paramsOrOptions as { isRaw?: boolean })?.isRaw;
      const message = isRaw ? keyOrMessage : t(keyOrMessage, paramsOrOptions);
      return toast.info(message, { duration: 4000 });
    },
    [t]
  );

  const loading = useCallback(
    (keyOrMessage: string, params?: Record<string, unknown>) => {
      const message = t(keyOrMessage, params);
      return toast.loading(message);
    },
    [t]
  );

  const promise = useCallback(
    <T>(
      promiseToWatch: Promise<T>,
      keys: {
        loading: string;
        success: string;
        error: string;
      }
    ) => {
      return toast.promise(promiseToWatch, {
        loading: t(keys.loading),
        success: t(keys.success),
        error: t(keys.error),
      });
    },
    [t]
  );

  const dismiss = useCallback((toastId?: string | number) => {
    toast.dismiss(toastId);
  }, []);

  return {
    success,
    error,
    warning,
    info,
    loading,
    promise,
    dismiss,
    // Raw toast for advanced usage
    toast,
  };
}

export type UseToastReturn = ReturnType<typeof useToast>;
