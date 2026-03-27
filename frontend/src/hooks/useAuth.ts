'use client'

import { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import type { User, AuthState, LoginCredentials, SignupCredentials } from '@/types/auth'

const AUTH_TOKEN_KEY = 'auth_token'

/**
 * Authentication Hook using REST API
 *
 * Replaces Supabase auth with JWT-based REST API authentication.
 */
export function useAuth(): AuthState & {
  login: (credentials: LoginCredentials) => Promise<{ success: boolean; error?: string }>
  signup: (credentials: SignupCredentials) => Promise<{ success: boolean; error?: string }>
  logout: () => void
  refreshToken: () => Promise<void>
} {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | undefined>()

  // Initialize auth on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = localStorage.getItem(AUTH_TOKEN_KEY)

        if (token) {
          // Set token on API client
          api.setToken(token)

          // Verify token and get user info
          const response = await api.get('/api/auth/me')

          if (response.success && response.user) {
            setUser(response.user)
          } else {
            // Invalid token, clear it
            localStorage.removeItem(AUTH_TOKEN_KEY)
            api.clearToken()
          }
        }
      } catch (err) {
        console.error('Auth initialization error:', err)
        // Clear invalid token
        localStorage.removeItem(AUTH_TOKEN_KEY)
        api.clearToken()
      } finally {
        setLoading(false)
      }
    }

    initAuth()
  }, [])

  /**
   * Login with email and password
   */
  const login = async (credentials: LoginCredentials): Promise<{ success: boolean; error?: string }> => {
    try {
      setError(undefined)
      setLoading(true)

      const response = await api.post('/api/auth/login', {
        email: credentials.email,
        password: credentials.password,
      })

      if (response.success && response.token && response.user) {
        // Save token to localStorage
        localStorage.setItem(AUTH_TOKEN_KEY, response.token)

        // Set token on API client
        api.setToken(response.token)

        // Set user state
        setUser(response.user)

        return { success: true }
      } else {
        const errorMsg = response.error || 'Login failed'
        setError(errorMsg)
        return { success: false, error: errorMsg }
      }
    } catch (err: any) {
      const errorMsg = err?.message || 'Network error during login'
      setError(errorMsg)
      return { success: false, error: errorMsg }
    } finally {
      setLoading(false)
    }
  }

  /**
   * Signup with email, password, and name
   */
  const signup = async (credentials: SignupCredentials): Promise<{ success: boolean; error?: string }> => {
    try {
      setError(undefined)
      setLoading(true)

      const response = await api.post('/api/auth/register', {
        email: credentials.email,
        password: credentials.password,
        full_name: credentials.full_name,
      })

      if (response.success && response.token && response.user) {
        // Save token to localStorage
        localStorage.setItem(AUTH_TOKEN_KEY, response.token)

        // Set token on API client
        api.setToken(response.token)

        // Set user state
        setUser(response.user)

        return { success: true }
      } else {
        const errorMsg = response.error || 'Signup failed'
        setError(errorMsg)
        return { success: false, error: errorMsg }
      }
    } catch (err: any) {
      const errorMsg = err?.message || 'Network error during signup'
      setError(errorMsg)
      return { success: false, error: errorMsg }
    } finally {
      setLoading(false)
    }
  }

  /**
   * Logout current user
   */
  const logout = () => {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    api.clearToken()
    setUser(null)
    setError(undefined)
  }

  /**
   * Refresh current session (re-fetch user data)
   */
  const refreshToken = async () => {
    try {
      const token = localStorage.getItem(AUTH_TOKEN_KEY)

      if (!token) {
        logout()
        return
      }

      api.setToken(token)
      const response = await api.get('/api/auth/me')

      if (response.success && response.user) {
        setUser(response.user)
      } else {
        logout()
      }
    } catch (err) {
      console.error('Token refresh error:', err)
      logout()
    }
  }

  return {
    user,
    loading,
    error,
    login,
    signup,
    logout,
    refreshToken,
  }
}

/**
 * Helper function to get auth token from localStorage
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

/**
 * Helper function to set auth token
 */
export function setAuthToken(token: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(AUTH_TOKEN_KEY, token)
  api.setToken(token)
}

/**
 * Helper function to clear auth token
 */
export function clearAuthToken(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(AUTH_TOKEN_KEY)
  api.clearToken()
}
