'use client'

import { useEffect, useState } from 'react'
import { User as SupabaseUser } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import type { AuthState, User } from '@/types/auth'

const convertUser = (supabaseUser: SupabaseUser | null): User | null => {
  if (!supabaseUser) return null

  return {
    id: supabaseUser.id,
    email: supabaseUser.email,
    full_name: (supabaseUser.user_metadata?.full_name as string) || undefined,
    avatar_url: (supabaseUser.user_metadata?.avatar_url as string) || undefined,
    role: (supabaseUser.user_metadata?.role as 'admin' | 'user' | 'viewer') || 'user',
  }
}

export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    loading: true,
  })

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      const user = convertUser(session?.user ?? null)
      setAuthState({
        user,
        loading: false,
      })
    })

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      const user = convertUser(session?.user ?? null)
      setAuthState({
        user,
        loading: false,
      })
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  return authState
}
