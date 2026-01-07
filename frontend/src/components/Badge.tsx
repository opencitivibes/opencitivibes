import React from 'react';
import { Check, Clock, X, Info, AlertTriangle, CheckCircle, XCircle, Edit2 } from 'lucide-react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | 'approved'
    | 'pending'
    | 'rejected'
    | 'pending_edit'
    | 'primary'
    | 'secondary'
    | 'success'
    | 'warning'
    | 'error'
    | 'info';
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  children: React.ReactNode;
  ref?: React.Ref<HTMLSpanElement>;
}

const statusIcons: Record<string, React.ReactNode> = {
  approved: <Check className="w-3 h-3" aria-hidden="true" />,
  pending: <Clock className="w-3 h-3" aria-hidden="true" />,
  rejected: <X className="w-3 h-3" aria-hidden="true" />,
  pending_edit: <Edit2 className="w-3 h-3" aria-hidden="true" />,
  success: <CheckCircle className="w-3 h-3" aria-hidden="true" />,
  warning: <AlertTriangle className="w-3 h-3" aria-hidden="true" />,
  error: <XCircle className="w-3 h-3" aria-hidden="true" />,
  info: <Info className="w-3 h-3" aria-hidden="true" />,
  primary: null,
  secondary: null,
};

export function Badge({
  variant = 'primary',
  size = 'md',
  showIcon = true,
  className = '',
  children,
  ref,
  ...props
}: BadgeProps) {
  const icon = showIcon ? statusIcons[variant] : null;
  const baseClasses = 'inline-flex items-center font-medium rounded-full whitespace-nowrap';

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-xs',
    lg: 'px-4 py-1.5 text-sm',
  };

  const variantClasses = {
    approved:
      'bg-success-100 dark:bg-success-900/70 text-success-800 dark:text-success-100 border border-success-200/50 dark:border-success-700/50',
    pending:
      'bg-warning-100 dark:bg-warning-800/80 text-warning-800 dark:text-warning-100 border border-warning-200/50 dark:border-warning-600/50',
    rejected:
      'bg-error-100 dark:bg-error-900/70 text-error-800 dark:text-error-100 border border-error-200/50 dark:border-error-700/50',
    pending_edit:
      'bg-purple-100 dark:bg-purple-900/70 text-purple-800 dark:text-purple-100 border border-purple-200/50 dark:border-purple-700/50',
    primary:
      'bg-primary-100 dark:bg-primary-900/70 text-primary-800 dark:text-primary-100 border border-primary-200/50 dark:border-primary-700/50',
    secondary:
      'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-100 border border-gray-200/50 dark:border-gray-600/50',
    success:
      'bg-success-100 dark:bg-success-900/70 text-success-800 dark:text-success-100 border border-success-200/50 dark:border-success-700/50',
    warning:
      'bg-warning-100 dark:bg-warning-800/80 text-warning-800 dark:text-warning-100 border border-warning-200/50 dark:border-warning-600/50',
    error:
      'bg-error-100 dark:bg-error-900/70 text-error-800 dark:text-error-100 border border-error-200/50 dark:border-error-700/50',
    info: 'bg-info-100 dark:bg-info-900/70 text-info-800 dark:text-info-100 border border-info-200/50 dark:border-info-700/50',
  };

  return (
    <span
      ref={ref}
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {icon && <span className="mr-1">{icon}</span>}
      {children}
    </span>
  );
}

// Count Badge Component (for notification counts, etc.)
export interface CountBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  count: number;
  max?: number;
  variant?: 'primary' | 'teal' | 'pink' | 'error';
  ref?: React.Ref<HTMLSpanElement>;
}

export function CountBadge({
  count,
  max = 99,
  variant = 'primary',
  className = '',
  ref,
  ...props
}: CountBadgeProps) {
  const displayCount = count > max ? `${max}+` : count.toString();

  const variantClasses = {
    primary: 'bg-primary-500 text-white',
    teal: 'bg-teal-500 text-white',
    pink: 'bg-pink-500 text-white',
    error: 'bg-error-500 text-white',
  };

  return (
    <span
      ref={ref}
      className={`inline-flex items-center justify-center w-6 h-6 text-xs font-bold rounded-full ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {displayCount}
    </span>
  );
}

// Dot Badge Component (for status indicators)
export interface DotBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'error' | 'info' | 'primary';
  ref?: React.Ref<HTMLSpanElement>;
}

export function DotBadge({ variant = 'primary', className = '', ref, ...props }: DotBadgeProps) {
  const variantClasses = {
    success: 'bg-success-500',
    warning: 'bg-warning-500',
    error: 'bg-error-500',
    info: 'bg-info-500',
    primary: 'bg-primary-500',
  };

  return (
    <span
      ref={ref}
      className={`inline-block w-2 h-2 rounded-full ${variantClasses[variant]} ${className}`}
      {...props}
    />
  );
}
