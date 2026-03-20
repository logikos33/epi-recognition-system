// Auth Types

export interface User {
  id: string
  email?: string
  full_name?: string
  avatar_url?: string
  role?: 'admin' | 'user' | 'viewer'
}

export interface AuthState {
  user: User | null
  loading: boolean
  error?: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface SignupCredentials {
  email: string
  password: string
  full_name: string
}

export interface Profile {
  id: string
  email: string
  full_name: string | null
  role: string
  company: string | null
  created_at: string
  updated_at: string
}
