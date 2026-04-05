import { createClient } from '@supabase/supabase-js'

// Get environment variables
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

// Debug logging (only in browser)
if (typeof window !== 'undefined') {
  console.log('=== SUPABASE CONFIG DEBUG ===')
  console.log('NEXT_PUBLIC_SUPABASE_URL:', supabaseUrl ? 'CONFIGURED' : 'MISSING')
  console.log('NEXT_PUBLIC_SUPABASE_ANON_KEY:', supabaseAnonKey ? 'CONFIGURED' : 'MISSING')
  console.log('Node ENV:', process.env.NODE_ENV)
  console.log('============================')
}

// Validate environment variables
if (!supabaseUrl) {
  throw new Error('NEXT_PUBLIC_SUPABASE_URL is missing. Please configure environment variables.')
}

if (!supabaseAnonKey) {
  throw new Error('NEXT_PUBLIC_SUPABASE_ANON_KEY is missing. Please configure environment variables.')
}

if (!supabaseUrl.startsWith('https://')) {
  throw new Error(`NEXT_PUBLIC_SUPABASE_URL is invalid: ${supabaseUrl}`)
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: false,
    flowType: 'implicit',
  },
})
