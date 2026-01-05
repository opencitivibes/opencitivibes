import { toast as sonnerToast, ExternalToast } from 'sonner';

/**
 * Toast utility functions with consistent configuration.
 * For i18n support, use the useToast hook instead.
 */

type ToastOptions = ExternalToast;

/**
 * Show a success toast
 */
export function toastSuccess(message: string, options?: ToastOptions) {
  return sonnerToast.success(message, {
    duration: 4000,
    ...options,
  });
}

/**
 * Show an error toast
 */
export function toastError(message: string, options?: ToastOptions) {
  return sonnerToast.error(message, {
    duration: 6000, // Errors stay longer
    ...options,
  });
}

/**
 * Show a warning toast
 */
export function toastWarning(message: string, options?: ToastOptions) {
  return sonnerToast.warning(message, {
    duration: 5000,
    ...options,
  });
}

/**
 * Show an info toast
 */
export function toastInfo(message: string, options?: ToastOptions) {
  return sonnerToast.info(message, {
    duration: 4000,
    ...options,
  });
}

/**
 * Show a loading toast that resolves to success or error
 */
export function toastPromise<T>(
  promise: Promise<T>,
  messages: {
    loading: string;
    success: string | ((data: T) => string);
    error: string | ((error: Error) => string);
  }
) {
  return sonnerToast.promise(promise, messages);
}

/**
 * Dismiss a specific toast or all toasts
 */
export function dismissToast(toastId?: string | number) {
  if (toastId) {
    sonnerToast.dismiss(toastId);
  } else {
    sonnerToast.dismiss();
  }
}

// Re-export for custom usage
export { sonnerToast as toast };
