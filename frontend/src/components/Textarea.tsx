import React, { useId } from 'react';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
  success?: boolean;
  helperText?: string;
  label?: string;
  fullWidth?: boolean;
  resize?: 'none' | 'vertical' | 'horizontal' | 'both';
  ref?: React.Ref<HTMLTextAreaElement>;
}

export function Textarea({
  error = false,
  success = false,
  helperText,
  label,
  fullWidth = true,
  resize = 'none',
  className = '',
  id,
  rows = 4,
  ref,
  ...props
}: TextareaProps) {
  const generatedId = useId();
  const textareaId = id || generatedId;

  const baseClasses =
    'px-4 py-3 rounded-lg text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 transition-colors duration-150 focus:outline-none';

  const widthClass = fullWidth ? 'w-full' : '';

  const resizeClasses = {
    none: 'resize-none',
    vertical: 'resize-y',
    horizontal: 'resize-x',
    both: 'resize',
  };

  const stateClasses = error
    ? 'border-2 border-error-500 focus:ring-2 focus:ring-error-500 focus:border-transparent'
    : success
      ? 'border-2 border-success-500 focus:ring-2 focus:ring-success-500 focus:border-transparent'
      : 'border border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-primary-500 focus:border-transparent';

  const disabledClasses = props.disabled
    ? 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed'
    : 'bg-white dark:bg-gray-700';

  return (
    <div className={fullWidth ? 'w-full' : ''}>
      {label && (
        <label
          htmlFor={textareaId}
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          {label}
        </label>
      )}
      <textarea
        ref={ref}
        id={textareaId}
        rows={rows}
        className={`${baseClasses} ${widthClass} ${resizeClasses[resize]} ${stateClasses} ${disabledClasses} ${className}`}
        {...props}
      />
      {helperText && (
        <p
          className={`mt-1.5 text-sm ${
            error ? 'text-error-600' : success ? 'text-success-600' : 'text-gray-500'
          }`}
        >
          {helperText}
        </p>
      )}
    </div>
  );
}
