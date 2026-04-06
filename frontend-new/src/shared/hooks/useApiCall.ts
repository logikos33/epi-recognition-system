import { useCallback, useState } from 'react'

interface ApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/**
 * Generic hook for API calls with loading/error state.
 */
export function useApiCall<T>(apiFn: (...args: unknown[]) => Promise<T>) {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: false,
    error: null,
  })

  const execute = useCallback(
    async (...args: unknown[]) => {
      setState((s) => ({ ...s, loading: true, error: null }))
      try {
        const data = await apiFn(...args)
        setState({ data, loading: false, error: null })
        return data
      } catch (err) {
        const message = (err as Error).message || 'Request failed'
        setState((s) => ({ ...s, loading: false, error: message }))
        throw err
      }
    },
    [apiFn]
  )

  return { ...state, execute }
}
