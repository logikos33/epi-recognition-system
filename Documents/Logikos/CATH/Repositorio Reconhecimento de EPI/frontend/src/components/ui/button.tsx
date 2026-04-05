import * as React from "react"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'destructive' | 'secondary'
  size?: 'default' | 'sm' | 'lg' | 'icon'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'default', size = 'default', ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none"
    const variants = {
      default: "bg-blue-600 text-white hover:bg-blue-700",
      outline: "border border-gray-300 bg-transparent hover:bg-gray-100",
      ghost: "hover:bg-gray-100",
      destructive: "bg-red-600 text-white hover:bg-red-700",
      secondary: "bg-gray-200 text-gray-900 hover:bg-gray-300"
    }
    const sizes = {
      default: "h-10 py-2 px-4",
      sm: "h-9 px-3 text-xs",
      lg: "h-11 px-8",
      icon: "h-10 w-10"
    }

    return (
      <button className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`} ref={ref} {...props} />
    )
  }
)
Button.displayName = "Button"

export { Button }
