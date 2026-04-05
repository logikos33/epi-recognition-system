import { forwardRef } from 'react';
import type { InputHTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, type = 'text', ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label className="text-sm font-medium text-text-secondary">
            {label}
          </label>
        )}
        <input
          ref={ref}
          type={type}
          className={cn(
            'px-3 py-2 bg-bg-tertiary border border-border rounded-md text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-blue focus:border-transparent transition-colors',
            error && 'border-accent-red focus:ring-accent-red',
            className
          )}
          {...props}
        />
        {error && (
          <span className="text-xs text-accent-red">{error}</span>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
