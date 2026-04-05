import * as React from "react"

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number
}

export function Progress({ className = '', value = 0, ...props }: ProgressProps) {
  return (
    <div className={`w-full bg-gray-200 rounded-full h-2 ${className}`} {...props}>
      <div
        className="bg-blue-600 h-2 rounded-full transition-all"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  )
}
