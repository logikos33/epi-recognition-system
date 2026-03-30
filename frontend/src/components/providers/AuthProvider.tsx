'use client'

import { useEffect } from 'react'
import { api } from '@/lib/api'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initialize API client with token from localStorage on mount
    const token = localStorage.getItem('auth_token')
    if (token) {
      api.setToken(token)
    }
  }, [])

  return <>{children}</>
}
