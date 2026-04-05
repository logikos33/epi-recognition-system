import * as React from "react"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outline' | 'secondary'
}

export function Badge({ className = '', variant = 'default', ...props }: BadgeProps) {
  const variants = {
    default: "bg-blue-600 text-white",
    outline: "border border-gray-300 text-gray-700",
    secondary: "bg-gray-200 text-gray-900"
  }

  return (
    <div className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${variants[variant]} ${className}`} {...props} />
  )
}
