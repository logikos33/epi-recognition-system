import { useEffect, useState } from 'react'
import { User } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'
import type { AuthState } from '@/types/auth'

export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    loading: true,
  })

  useEffect(() => {
    // Get initial session
    const getInitialSession = async () => {
      const {
        data: { session },
        error,
      } = await supabase.auth.getSession()

      if (error) {
        setAuthState({
          user: null,
          loading: false,
          error: error.message,
        })
        return
      }

      const user: User | null = session?.user ?? null
      setAuthState({
        user,
        loading: false,
      })
    }

    getInitialSession()

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      const user: User | null = session?.user ?? null
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
