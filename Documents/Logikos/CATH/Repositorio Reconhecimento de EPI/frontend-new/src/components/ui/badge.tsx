import { forwardRef } from 'react';
import type { HTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'error' | 'info' | 'default';
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', children, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
          {
            'bg-accent-green/10 text-accent-green border border-accent-green/20': variant === 'success',
            'bg-accent-amber/10 text-accent-amber border border-accent-amber/20': variant === 'warning',
            'bg-accent-red/10 text-accent-red border border-accent-red/20': variant === 'error',
            'bg-accent-blue/10 text-accent-blue border border-accent-blue/20': variant === 'info',
            'bg-bg-tertiary text-text-secondary border border-border': variant === 'default',
          },
          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';
