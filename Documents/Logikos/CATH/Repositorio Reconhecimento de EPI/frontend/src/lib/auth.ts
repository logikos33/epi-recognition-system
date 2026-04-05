import { api } from './api'

export interface User {
  id: string
  email: string
  full_name?: string
  company_name?: string
}

export interface AuthResponse {
  success: boolean
  user: User
  token: string
}

export async function signIn(credentials: { email: string; password: string }): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/api/auth/login', credentials)
  if (response.success && response.token) {
    api.setToken(response.token)
    if (typeof window !== 'undefined') {
      localStorage.setItem('user', JSON.stringify(response.user))
    }
  }
  return response
}

export function signOut() {
  api.clearToken()
  if (typeof window !== 'undefined') localStorage.removeItem('user')
}

export function getCurrentUser(): User | null {
  if (typeof window !== 'undefined') {
    const userStr = localStorage.getItem('user')
    return userStr ? JSON.parse(userStr) : null
  }
  return null
}

export function isAuthenticated(): boolean {
  return !!api.getToken()
}
