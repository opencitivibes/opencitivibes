import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'standard' | 'featured' | 'interactive';
  children: React.ReactNode;
  ref?: React.Ref<HTMLDivElement>;
}

export function Card({ variant = 'standard', className = '', children, ref, ...props }: CardProps) {
  const baseClasses = 'rounded-xl p-6';

  const variantClasses = {
    standard:
      'bg-white dark:bg-gray-800 shadow-md hover:shadow-lg transition-shadow duration-200 border border-gray-100 dark:border-gray-700',
    featured: 'bg-gradient-to-br from-primary-500 to-primary-700 shadow-xl text-white',
    interactive:
      'bg-white dark:bg-gray-800 shadow-md hover:shadow-xl transition-all duration-200 border border-gray-100 dark:border-gray-700 cursor-pointer hover:-translate-y-1 hover:border-primary-200 dark:hover:border-primary-600',
  };

  return (
    <div ref={ref} className={`${baseClasses} ${variantClasses[variant]} ${className}`} {...props}>
      {children}
    </div>
  );
}

// Card Header Component
export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  ref?: React.Ref<HTMLDivElement>;
}

export function CardHeader({ className = '', children, ref, ...props }: CardHeaderProps) {
  return (
    <div ref={ref} className={`mb-4 ${className}`} {...props}>
      {children}
    </div>
  );
}

// Card Title Component
export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode;
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
  ref?: React.Ref<HTMLHeadingElement>;
}

export function CardTitle({
  as: Component = 'h3',
  className = '',
  children,
  ref,
  ...props
}: CardTitleProps) {
  return (
    <Component
      ref={ref as React.Ref<HTMLHeadingElement>}
      className={`text-xl font-bold mb-2 ${className}`}
      {...props}
    >
      {children}
    </Component>
  );
}

// Card Content Component
export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  ref?: React.Ref<HTMLDivElement>;
}

export function CardContent({ className = '', children, ref, ...props }: CardContentProps) {
  return (
    <div ref={ref} className={`text-base ${className}`} {...props}>
      {children}
    </div>
  );
}

// Card Footer Component
export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  ref?: React.Ref<HTMLDivElement>;
}

export function CardFooter({ className = '', children, ref, ...props }: CardFooterProps) {
  return (
    <div
      ref={ref}
      className={`mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
