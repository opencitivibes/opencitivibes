import React, { useId } from 'react';

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  error?: boolean;
  success?: boolean;
  helperText?: string;
  label?: string;
  fullWidth?: boolean;
  ref?: React.Ref<HTMLInputElement>;
}

export function Input({
  error = false,
  success = false,
  helperText,
  label,
  fullWidth = true,
  className = '',
  id,
  ref,
  ...props
}: InputProps) {
  const generatedId = useId();
  const inputId = id || generatedId;

  const baseClasses =
    'px-4 py-2.5 rounded-lg text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 transition-colors duration-150 focus:outline-none';

  const widthClass = fullWidth ? 'w-full' : '';

  const stateClasses = error
    ? 'border-2 border-error-500 focus:ring-2 focus:ring-error-500 focus:border-transparent'
    : success
      ? 'border-2 border-success-500 focus:ring-2 focus:ring-success-500 focus:border-transparent'
      : 'border border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-primary-500 focus:border-transparent';

  const disabledClasses = props.disabled
    ? 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed'
    : 'bg-white dark:bg-gray-800';

  return (
    <div className={fullWidth ? 'w-full' : ''}>
      {label && (
        <label
          htmlFor={inputId}
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={`${baseClasses} ${widthClass} ${stateClasses} ${disabledClasses} ${className}`}
        {...props}
      />
      {helperText && (
        <p
          className={`mt-1.5 text-sm ${
            error
              ? 'text-error-600'
              : success
                ? 'text-success-600'
                : 'text-gray-500 dark:text-gray-400'
          }`}
        >
          {helperText}
        </p>
      )}
    </div>
  );
}
