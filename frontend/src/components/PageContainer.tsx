import React from 'react';

export interface PageContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  /**
   * Maximum width of the container
   * @default '7xl' (1280px)
   */
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl' | '5xl' | '6xl' | '7xl' | 'full';
  /**
   * Vertical padding
   * @default 'normal' (py-8)
   */
  paddingY?: 'none' | 'tight' | 'normal' | 'loose' | 'xl';
  /**
   * Horizontal padding
   * @default true
   */
  paddingX?: boolean;
  ref?: React.Ref<HTMLDivElement>;
}

export function PageContainer({
  children,
  maxWidth = '7xl',
  paddingY = 'normal',
  paddingX = true,
  className = '',
  ref,
  ...props
}: PageContainerProps) {
  const maxWidthClasses = {
    sm: 'max-w-sm', // 640px
    md: 'max-w-md', // 768px
    lg: 'max-w-lg', // 1024px
    xl: 'max-w-xl', // 1280px
    '2xl': 'max-w-2xl', // 1536px
    '3xl': 'max-w-3xl',
    '4xl': 'max-w-4xl',
    '5xl': 'max-w-5xl',
    '6xl': 'max-w-6xl',
    '7xl': 'max-w-7xl', // 1280px - Default
    full: 'max-w-full',
  };

  const paddingYClasses = {
    none: '',
    tight: 'py-4', // 16px
    normal: 'py-8', // 32px
    loose: 'py-12', // 48px
    xl: 'py-16', // 64px
  };

  const paddingXClass = paddingX ? 'px-4 sm:px-6 lg:px-8' : '';

  return (
    <div
      ref={ref}
      className={`${maxWidthClasses[maxWidth]} mx-auto ${paddingXClass} ${paddingYClasses[paddingY]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

// Page Header Component
export interface PageHeaderProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title: React.ReactNode;
  description?: string;
  actions?: React.ReactNode;
  children?: React.ReactNode;
  ref?: React.Ref<HTMLDivElement>;
}

export function PageHeader({
  title,
  description,
  actions,
  children,
  className = '',
  ref,
  ...props
}: PageHeaderProps) {
  return (
    <div ref={ref} className={`mb-8 ${className}`} {...props}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">{title}</h1>
          {description && (
            <p className="text-base text-gray-600 dark:text-gray-400">{description}</p>
          )}
        </div>
        {actions && <div className="flex-shrink-0">{actions}</div>}
      </div>
      {children}
    </div>
  );
}

// Section Component
export interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode;
  /**
   * Spacing between sections
   * @default 'normal' (mb-8)
   */
  spacing?: 'tight' | 'normal' | 'loose';
  ref?: React.Ref<HTMLElement>;
}

export function Section({
  children,
  spacing = 'normal',
  className = '',
  ref,
  ...props
}: SectionProps) {
  const spacingClasses = {
    tight: 'mb-4', // 16px
    normal: 'mb-8', // 32px
    loose: 'mb-12', // 48px
  };

  return (
    <section ref={ref} className={`${spacingClasses[spacing]} ${className}`} {...props}>
      {children}
    </section>
  );
}

// Grid Component for card layouts
export interface GridProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  /**
   * Number of columns
   * @default 3 (responsive: 1 on mobile, 2 on tablet, 3 on desktop)
   */
  cols?: 1 | 2 | 3 | 4;
  /**
   * Gap between grid items
   * @default 'normal' (gap-4 = 16px)
   */
  gap?: 'tight' | 'normal' | 'loose';
  ref?: React.Ref<HTMLDivElement>;
}

export function Grid({
  children,
  cols = 3,
  gap = 'normal',
  className = '',
  ref,
  ...props
}: GridProps) {
  const colsClasses = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
  };

  const gapClasses = {
    tight: 'gap-3', // 12px
    normal: 'gap-4', // 16px
    loose: 'gap-6', // 24px
  };

  return (
    <div
      ref={ref}
      className={`grid ${colsClasses[cols]} ${gapClasses[gap]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
