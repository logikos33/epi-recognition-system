import { type ReactNode } from 'react'
import { useAuth } from '../context/AuthContext'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

export function ProtectedRoute({ children, fallback }: Props) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>
  }

  if (!isAuthenticated) {
    return fallback ?? (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>Please log in to access this page.</p>
        <a href="/login">Go to Login</a>
      </div>
    )
  }

  return <>{children}</>
}
