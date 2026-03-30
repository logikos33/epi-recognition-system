import { api, API_ENDPOINTS } from './api'
import type { LoginCredentials, SignupCredentials } from '@/types/auth'

interface AuthResponse {
  token: string
  user: {
    id: string
    email: string
    full_name: string
    company_name?: string
    created_at: string
  }
}

interface AuthData {
  user: AuthResponse['user']
  session: {
    access_token: string
    token_type: string
    expires_in: number
  }
}

interface AuthError extends Error {
  message: string
}

export async function signUp(credentials: SignupCredentials) {
  try {
    const response = await api.post(API_ENDPOINTS.AUTH_REGISTER, {
      email: credentials.email,
      password: credentials.password,
      full_name: credentials.full_name,
      company_name: (credentials as any).company_name || '',
    })

    // Store token for future requests
    if (response.token) {
      api.setToken(response.token)
      // Also store in localStorage for persistence
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', response.token)
      }
    }

    // Transform response to match expected format
    const data: AuthData = {
      user: response.user,
      session: {
        access_token: response.token,
        token_type: 'Bearer',
        expires_in: 86400, // 24 hours
      },
    }

    return { data, error: null }
  } catch (error) {
    const authError: AuthError = error as AuthError
    return { data: null, error: authError }
  }
}

export async function signIn(credentials: LoginCredentials) {
  try {
    const response = await api.post(API_ENDPOINTS.AUTH_LOGIN, {
      email: credentials.email,
      password: credentials.password,
    })

    // Store token for future requests
    if (response.token) {
      api.setToken(response.token)
      // Also store in localStorage for persistence
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', response.token)
      }
    }

    // Transform response to match expected format
    const data: AuthData = {
      user: response.user,
      session: {
        access_token: response.token,
        token_type: 'Bearer',
        expires_in: 86400, // 24 hours
      },
    }

    return { data, error: null }
  } catch (error) {
    const authError: AuthError = error as AuthError
    return { data: null, error: authError }
  }
}

export async function signOut() {
  try {
    await api.post(API_ENDPOINTS.AUTH_LOGOUT)

    // Clear token from API client and localStorage
    api.clearToken()
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
    }

    return { error: null }
  } catch (error) {
    const authError: AuthError = error as AuthError
    return { error: authError }
  }
}

export async function getCurrentUser() {
  try {
    const token = api.getToken()
    if (!token) {
      // Try to get token from localStorage
      if (typeof window !== 'undefined') {
        const storedToken = localStorage.getItem('auth_token')
        if (storedToken) {
          api.setToken(storedToken)
        } else {
          return { user: null, error: new Error('No authentication token found') }
        }
      } else {
        return { user: null, error: new Error('No authentication token found') }
      }
    }

    const response = await api.get(API_ENDPOINTS.AUTH_ME)
    return { user: response.user, error: null }
  } catch (error) {
    const authError: AuthError = error as AuthError
    // If unauthorized, clear the token
    if (authError.message.includes('401') || authError.message.includes('Unauthorized')) {
      api.clearToken()
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token')
      }
    }
    return { user: null, error: authError }
  }
}

export async function resetPassword(email: string) {
  // TODO: Implement password reset when backend supports it
  // For now, return an error indicating this feature is not implemented
  return {
    data: null,
    error: new Error('Password reset not implemented yet')
  }
}
