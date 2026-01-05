import React from 'react';

export interface FormFieldProps extends React.HTMLAttributes<HTMLDivElement> {
  label?: string;
  htmlFor?: string;
  error?: string;
  helperText?: string;
  required?: boolean;
  children: React.ReactNode;
  ref?: React.Ref<HTMLDivElement>;
}

export function FormField({
  label,
  htmlFor,
  error,
  helperText,
  required = false,
  className = '',
  children,
  ref,
  ...props
}: FormFieldProps) {
  return (
    <div ref={ref} className={`space-y-2 ${className}`} {...props}>
      {label && (
        <label htmlFor={htmlFor} className="block text-sm font-medium text-gray-700">
          {label}
          {required && <span className="text-error-500 ml-1">*</span>}
        </label>
      )}
      {children}
      {error && (
        <p className="text-sm text-error-600 flex items-start mt-1.5">
          <svg
            className="w-4 h-4 mr-1 mt-0.5 flex-shrink-0"
            fill="currentColor"
            viewBox="0 0 20 20"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          {error}
        </p>
      )}
      {helperText && !error && <p className="text-sm text-gray-500 mt-1.5">{helperText}</p>}
    </div>
  );
}

// Form Group Component (for organizing multiple fields)
export interface FormGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  spacing?: 'tight' | 'normal' | 'loose';
  ref?: React.Ref<HTMLDivElement>;
}

export function FormGroup({
  children,
  spacing = 'normal',
  className = '',
  ref,
  ...props
}: FormGroupProps) {
  const spacingClasses = {
    tight: 'space-y-3',
    normal: 'space-y-4',
    loose: 'space-y-6',
  };

  return (
    <div ref={ref} className={`${spacingClasses[spacing]} ${className}`} {...props}>
      {children}
    </div>
  );
}
