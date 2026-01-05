import React, { useId } from 'react';

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
  success?: boolean;
  helperText?: string;
  label?: string;
  fullWidth?: boolean;
  children: React.ReactNode;
  ref?: React.Ref<HTMLSelectElement>;
}

export function Select({
  error = false,
  success = false,
  helperText,
  label,
  fullWidth = true,
  className = '',
  id,
  children,
  ref,
  ...props
}: SelectProps) {
  const generatedId = useId();
  const selectId = id || generatedId;

  const baseClasses =
    'px-4 py-2.5 rounded-lg text-gray-900 dark:text-gray-100 transition-colors duration-150 focus:outline-none appearance-none bg-white dark:bg-gray-800';

  const widthClass = fullWidth ? 'w-full' : '';

  const stateClasses = error
    ? 'border-2 border-error-500 focus:ring-2 focus:ring-error-500 focus:border-transparent'
    : success
      ? 'border-2 border-success-500 focus:ring-2 focus:ring-success-500 focus:border-transparent'
      : 'border border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-primary-500 focus:border-transparent';

  const disabledClasses = props.disabled
    ? 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed'
    : 'bg-white dark:bg-gray-800 cursor-pointer';

  return (
    <div className={fullWidth ? 'w-full' : ''}>
      {label && (
        <label
          htmlFor={selectId}
          className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2"
        >
          {label}
        </label>
      )}
      <div className="relative">
        <select
          ref={ref}
          id={selectId}
          className={`${baseClasses} ${widthClass} ${stateClasses} ${disabledClasses} ${className}`}
          style={{ colorScheme: 'dark light' }}
          {...props}
        >
          {children}
        </select>
        {/* Custom dropdown arrow */}
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-gray-500 dark:text-gray-400">
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
      {helperText && (
        <p
          className={`mt-1.5 text-sm ${
            error
              ? 'text-error-600 dark:text-error-400'
              : success
                ? 'text-success-600 dark:text-success-400'
                : 'text-gray-500 dark:text-gray-400'
          }`}
        >
          {helperText}
        </p>
      )}
    </div>
  );
}
