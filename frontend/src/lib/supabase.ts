import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

// Log environment variables in development for debugging
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  console.log('Supabase URL configured:', !!supabaseUrl)
  console.log('Supabase Key configured:', !!supabaseAnonKey)
}

if (!supabaseUrl || !supabaseUrl.startsWith('https://')) {
  console.error('Invalid NEXT_PUBLIC_SUPABASE_URL:', supabaseUrl)
  throw new Error('NEXT_PUBLIC_SUPABASE_URL is not configured correctly')
}

if (!supabaseAnonKey || supabaseAnonKey.length < 10) {
  console.error('Invalid NEXT_PUBLIC_SUPABASE_ANON_KEY')
  throw new Error('NEXT_PUBLIC_SUPABASE_ANON_KEY is not configured correctly')
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: false,
    flowType: 'implicit',
  },
})
