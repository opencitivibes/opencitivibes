'use client';

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'success' | 'error' | 'warning' | 'info';
  title?: string;
  dismissible?: boolean;
  onDismiss?: () => void;
  children: React.ReactNode;
  ref?: React.Ref<HTMLDivElement>;
}

export function Alert({
  variant = 'info',
  title,
  dismissible = false,
  onDismiss,
  className = '',
  children,
  ref,
  ...props
}: AlertProps) {
  const { t } = useTranslation();
  const [isVisible, setIsVisible] = useState(true);

  const handleDismiss = () => {
    setIsVisible(false);
    if (onDismiss) {
      onDismiss();
    }
  };

  if (!isVisible) return null;

  const variantClasses = {
    success: {
      container: 'bg-success-50 dark:bg-success-900/30 border-success-500',
      icon: 'text-success-500 dark:text-success-400',
      title: 'text-success-800 dark:text-success-200',
      text: 'text-success-700 dark:text-success-300',
    },
    error: {
      container: 'bg-error-50 dark:bg-error-900/30 border-error-500',
      icon: 'text-error-500 dark:text-error-400',
      title: 'text-error-800 dark:text-error-200',
      text: 'text-error-700 dark:text-error-300',
    },
    warning: {
      container: 'bg-warning-50 dark:bg-warning-900/30 border-warning-500',
      icon: 'text-warning-500 dark:text-warning-400',
      title: 'text-warning-800 dark:text-warning-200',
      text: 'text-warning-700 dark:text-warning-300',
    },
    info: {
      container: 'bg-info-50 dark:bg-info-900/30 border-info-500',
      icon: 'text-info-500 dark:text-info-400',
      title: 'text-info-800 dark:text-info-200',
      text: 'text-info-700 dark:text-info-300',
    },
  };

  const icons = {
    success: (
      <svg
        className="w-5 h-5"
        fill="currentColor"
        viewBox="0 0 20 20"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
          clipRule="evenodd"
        />
      </svg>
    ),
    error: (
      <svg
        className="w-5 h-5"
        fill="currentColor"
        viewBox="0 0 20 20"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
          clipRule="evenodd"
        />
      </svg>
    ),
    warning: (
      <svg
        className="w-5 h-5"
        fill="currentColor"
        viewBox="0 0 20 20"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          fillRule="evenodd"
          d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
          clipRule="evenodd"
        />
      </svg>
    ),
    info: (
      <svg
        className="w-5 h-5"
        fill="currentColor"
        viewBox="0 0 20 20"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
          clipRule="evenodd"
        />
      </svg>
    ),
  };

  return (
    <div
      ref={ref}
      className={`border-l-4 p-4 rounded-r-lg ${variantClasses[variant].container} ${className}`}
      role="alert"
      {...props}
    >
      <div className="flex items-start">
        <div className={`flex-shrink-0 ${variantClasses[variant].icon}`}>{icons[variant]}</div>
        <div className="ml-3 flex-1">
          {title && (
            <h3 className={`text-sm font-medium mb-1 ${variantClasses[variant].title}`}>{title}</h3>
          )}
          <div className={`text-sm ${variantClasses[variant].text}`}>{children}</div>
        </div>
        {dismissible && (
          <button
            type="button"
            className={`ml-3 inline-flex flex-shrink-0 justify-center items-center h-5 w-5 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 ${variantClasses[variant].text} hover:opacity-75 transition-opacity`}
            onClick={handleDismiss}
            aria-label={t('common.close')}
          >
            <svg
              className="w-4 h-4"
              fill="currentColor"
              viewBox="0 0 20 20"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
