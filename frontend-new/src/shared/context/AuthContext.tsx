/**
 * Auth context — JWT with expiry validation.
 * isAuthenticated() validates exp, not just token existence.
 */
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { decodeToken, getValidToken, isTokenValid } from '../lib/jwt'

interface User {
  id: string
  email: string
  full_name?: string
}

interface AuthContextValue {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (token: string, user: User) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Initialize from localStorage — validate expiry on mount
  useEffect(() => {
    const storedToken = getValidToken()
    if (storedToken) {
      const payload = decodeToken(storedToken)
      const storedUser = localStorage.getItem('user')
      setToken(storedToken)
      setUser(
        storedUser
          ? JSON.parse(storedUser)
          : payload
          ? { id: payload.user_id || payload.sub, email: payload.email }
          : null
      )
    }
    setIsLoading(false)
  }, [])

  // Auto-logout when token expires
  useEffect(() => {
    if (!token) return
    const payload = decodeToken(token)
    if (!payload) return

    const msUntilExpiry = (payload.exp - Math.floor(Date.now() / 1000)) * 1000
    if (msUntilExpiry <= 0) {
      logout()
      return
    }

    const timer = setTimeout(() => logout(), msUntilExpiry)
    return () => clearTimeout(timer)
  }, [token])

  const login = useCallback((newToken: string, newUser: User) => {
    if (!isTokenValid(newToken)) {
      console.error('[Auth] Attempted to store invalid/expired token')
      return
    }
    localStorage.setItem('token', newToken)
    localStorage.setItem('user', JSON.stringify(newUser))
    setToken(newToken)
    setUser(newUser)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      token,
      isAuthenticated: isTokenValid(token),
      isLoading,
      login,
      logout,
    }),
    [user, token, isLoading, login, logout]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
